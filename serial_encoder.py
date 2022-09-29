from amaranth import *
from amaranth.sim import *

from bcd import BinToBcd

import math

# this encoder transfors sequences of bytes into integer representation
# it is connected to a UART TX and will send the transformed sequence on
# the wire. every sequence of integers is terminated by '\r\n'.
# to use the encoder, fill the buffer with bytes, and raise the trg signal.

class SerialEncoder(Elaboratable):
    def __init__(self, bufsize=16):
        self.bufsize = bufsize

        self.data = Signal(unsigned(32))
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
        bcd = BinToBcd(bits=32)
        buffer = Array([Signal(unsigned(32)) for _ in range(self.bufsize)])
        size = Signal(unsigned(8))

        m = Module()

        m.submodules.bcd = bcd

        bytes_to_encode = Signal(unsigned(8))
        pos = Signal(8)
        bcd_pos = Signal(unsigned(5))
        seen_nonzero = Signal()

        with m.FSM(reset="IDLE"):

            with m.State("IDLE"):
                m.d.sync += self.rdy.eq(0)
                with m.If(self.trg == 1):
                    m.d.sync += [
                        bytes_to_encode.eq(size),
                        pos.eq(0)
                    ]
                    m.next = "ENCODE"
                with m.If(self.write == 1):
                    m.d.sync += [
                        size.eq(size + 1),
                        buffer[size].eq(self.data)
                    ]
                    m.next = "IDLE"

            with m.State("ENCODE"):
                with m.If(bytes_to_encode > 0):
                    m.next = "LOAD"
                with m.Else():
                    m.next = "SEND_TERMINATOR1"

            with m.State("LOAD"):
                m.d.sync += [
                    bcd.bin.eq(buffer[pos]),
                    bcd.trg.eq(1),
                    bcd_pos.eq(0),
                    seen_nonzero.eq(0)
                ]
                m.next = "BCD_TRG_OFF"

            with m.State("BCD_TRG_OFF"):
                m.d.sync += bcd.trg.eq(0)
                m.next = "CONVERT_BCD"

            with m.State("CONVERT_BCD"):
                with m.If(bcd.rdy == 1):
                    m.next = "SEND_BCD"

            with m.State("SEND_BCD"):
                with m.If(bcd_pos < 11):
                    digit = bcd.bcd.word_select(10 - bcd_pos, 4)
                    m.d.sync += bcd_pos.eq(bcd_pos + 1)
                    with m.If((bcd_pos == bcd.digits) |
                        (digit != 0) | (seen_nonzero == 1)):
                        m.d.sync += [
                            seen_nonzero.eq(1),
                            self.tx.eq(digit + ord('0')),
                            self.tx_trg.eq(1),
                        ]
                        m.next = "WAIT_TX"
                    with m.Else():
                        m.next = "SEND_BCD"
                with m.Else():
                    m.next = "SEND_SPACER"

            with m.State("WAIT_TX"):
                m.d.sync += self.tx_trg.eq(0)
                m.next = "WAIT_TX2"

            with m.State("WAIT_TX2"):
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
                m.next = "SEND_SPACER3"

            with m.State("SEND_SPACER3"):
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
                m.next = "SEND_TERMINATOR3"

            with m.State("SEND_TERMINATOR3"):
                with m.If(self.tx_rdy == 1):
                    m.next = "SEND_TERMINATOR4"

            with m.State("SEND_TERMINATOR4"):
                m.d.sync += [
                    self.tx.eq(ord('\n')),
                    self.tx_trg.eq(1)
                ]
                m.next = "SEND_TERMINATOR5"

            with m.State("SEND_TERMINATOR5"):
                m.d.sync += self.tx_trg.eq(0)
                m.next = "SEND_TERMINATOR6"

            with m.State("SEND_TERMINATOR6"):
                with m.If(self.tx_rdy == 1):
                    m.next = "DONE"

            with m.State("DONE"):
                m.d.sync += [
                    self.rdy.eq(1),
                    size.eq(0)
                ]
                m.next = "IDLE"

        return m

if __name__ == '__main__':
    dut = SerialEncoder(bufsize=16)

    sim = Simulator(dut)

    def wait_convert():
        for i in range(10 * 4):
            yield

    def mimic_tx_rdy():
        for i in range(10):
            yield
        yield dut.tx_rdy.eq(1)
        yield
        yield dut.tx_rdy.eq(0)
        yield

    def transmit(n):
        yield dut.trg.eq(1)
        yield
        yield dut.trg.eq(0)
        yield
        for i in range(n):
            yield from wait_convert()
            yield from mimic_tx_rdy()

    def write(char):
        yield dut.data.eq(char)
        yield dut.write.eq(1)
        yield
        yield dut.write.eq(0)
        yield

    def check_init():
        yield
        assert(yield dut.rdy == 0)

    def check_empty():
        yield from transmit(2)

    def check_write():
        yield from write(0x4)
        yield from write(0x0a)
        yield from write(0xfe)
        yield from write(0x1337)
        yield from write(0x133713)
        yield from write(0x13371337)
        yield from transmit(40)
        for i in range(200):
            yield

    def proc():
        yield from check_init()
        yield from check_empty()
        yield from check_write()


    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('serial_enc.vcd', 'serial_enc_orig.gtkw', traces=dut.ports):
        sim.run()
