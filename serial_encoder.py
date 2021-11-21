from nmigen import *
from nmigen.sim import *

import math

# this encoder transfors sequences of bytes into integer representation
# it is connected to a UART TX and will send the transformed sequence on
# the wire. every sequence of integers is terminated by '\r\n'.
# to use the encoder, fill the buffer with bytes, and raise the trg signal.

class SerialEncoder(Elaboratable):
    def __init__(self, bufsize=16):
        self.bufsize = bufsize
        self.buffer = Array([Signal(unsigned(8)) for _ in range(self.bufsize)])
        self.len = Signal(unsigned(8))

        self.data = Signal(unsigned(8))
        self.write = Signal()
        self.trg = Signal()
        self.rdy = Signal()
        self.tx = Signal(unsigned(8))
        self.tx_rdy = Signal()
        self.tx_trg = Signal()

        self.ports = [
                self.write,
                self.data,
                self.trg,
                self.rdy,
                self.tx,
                self.tx_rdy,
                self.tx_trg
                ]

    def elaborate(self, platform):
        m = Module()

        bytes_to_encode = Signal(unsigned(8))
        byte = Signal(8)
        pos = Signal(8)
        bcd = Array([Signal(unsigned(4)) for _ in range(3)])
        bcd_len = Signal(4)
        bcd_pos = Signal(4)

        with m.FSM(reset="IDLE"):

            with m.State("IDLE"):
                m.d.sync += self.rdy.eq(0)
                with m.If(self.trg == 1):
                    m.d.sync += [
                            bytes_to_encode.eq(self.len),
                            pos.eq(0)
                            ]
                    m.next = "ENCODE"
                with m.If(self.write == 1):
                    m.d.sync += [
                            self.len.eq(self.len + 1),
                            self.buffer[self.len].eq(self.data)
                            ]
                    m.next = "IDLE"

            with m.State("ENCODE"):
                with m.If(bytes_to_encode > 0):
                    m.next = "LOAD"
                with m.Else():
                    m.next = "SEND_TERMINATOR1"

            with m.State("LOAD"):
                m.d.sync += [
                        byte.eq(self.buffer[pos]),
                        bcd_len.eq(0),
                        bcd_pos.eq(0)
                        ]
                m.next = "CONVERT_BCD"

            with m.State("CONVERT_BCD"):
                with m.If(byte > 0):
                    m.d.sync += [
                            bcd[bcd_len].eq(byte % 10),
                            bcd_len.eq(bcd_len + 1),
                            byte.eq(byte // 10)
                            ]
                with m.Else():
                    m.next = "SEND_BCD"

            with m.State("SEND_BCD"):
                with m.If(bcd_pos < bcd_len):
                    m.d.sync += [
                            self.tx.eq(bcd[bcd_len - bcd_pos - 1]),
                            self.tx_trg.eq(1),
                            bcd_pos.eq(bcd_pos + 1)
                            ]
                    m.next = "WAIT_TX"
                with m.Else():
                    m.next = "SEND_SPACER"

            with m.State("WAIT_TX"):
                m.d.sync += self.tx_trg.eq(0)
                with m.If(self.tx_rdy == 1):
                    m.next = "SEND_BCD"

            with m.State("SEND_SPACER"):
                m.d.sync += [
                        self.tx.eq(ord(' ')),
                        self.tx_trg.eq(1)
                        ]
                m.next = "SEND_SPACER2"

            with m.State("SEND_SPACER2"):
                m.d.sync += self.tx_trg.eq(0)
                with m.If(self.tx_rdy == 1):
                    m.next = "ADVANCE"

            with m.State("ADVANCE"):
                with m.If(bytes_to_encode > 0):
                    m.d.sync += [
                            bytes_to_encode.eq(bytes_to_encode - 1),
                            pos.eq(pos + 1)
                            ]
                m.next = "ENCODE"

            with m.State("SEND_TERMINATOR1"):
                m.d.sync += [
                        self.tx.eq(ord('\r')),
                        self.tx_trg.eq(1)
                        ]
                m.next = "SEND_TERMINATOR2"

            with m.State("SEND_TERMINATOR2"):
                m.d.sync += self.tx_trg.eq(0)
                with m.If(self.tx_rdy == 1):
                    m.next = "SEND_TERMINATOR3"

            with m.State("SEND_TERMINATOR3"):
                m.d.sync += [
                        self.tx.eq(ord('\n')),
                        self.tx_trg.eq(1)
                        ]
                m.next = "SEND_TERMINATOR4"

            with m.State("SEND_TERMINATOR4"):
                m.d.sync += self.tx_trg.eq(0)
                with m.If(self.tx_rdy == 1):
                    m.next = "DONE"

            with m.State("DONE"):
                m.d.sync += [
                        self.rdy.eq(1),
                        self.len.eq(0)
                        ]
                m.next = "IDLE"

        return m

if __name__ == '__main__':
    dut = SerialEncoder(bufsize=16)

    sim = Simulator(dut)

    def tick():
        yield Tick()
        yield Settle()

    def write(char):
        yield dut.data.eq(char)
        yield dut.write.eq(1)
        yield from tick()
        yield dut.write.eq(0)
        yield from tick()

    def check_init():
        yield from tick()
        assert(yield dut.len == 0)
        assert(yield dut.rdy == 0)

    def check_empty():
        yield from transmit(2)

    def transmit(n):
        yield dut.trg.eq(1)
        yield from tick()
        yield dut.trg.eq(0)
        yield from tick()
        for i in range(n):
            yield from wait_convert()
            yield from mimic_tx_rdy()

    def wait_convert():
        for i in range(5):
            yield from tick()

    def mimic_tx_rdy():
        for i in range(10):
            yield from tick()
        yield dut.tx_rdy.eq(1)
        yield from tick()
        yield dut.tx_rdy.eq(0)
        yield from tick()

    def check_write():
        yield from write(0x4)
        yield from write(0x0a)
        yield from write(0xfe)
        yield from transmit(11)

    def proc():
        yield from check_init()
        yield from check_empty()
        yield from check_write()


    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('serial_enc.vcd', 'serial_enc.gtkw', traces=dut.ports):
        sim.run()
