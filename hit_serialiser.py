from amaranth import *
from amaranth.sim import *

# this encoder transfors sequences of hits into bytes for UART transmission.
# it is connected to a FIFO on the input and a UART TX on the output and will
# send the transformed sequence on the wire.

# Output format is:
# byte 0: index number
# bytes 1-4: 32-bit value
# byte 5: 0xff

class HitSerialiser(Elaboratable):
    def __init__(self, bits=32, n_bytes=6):
        self.bits = bits
        self.n_bytes = n_bytes
        self.fifo_rdy = Signal()
        self.fifo_r_data = Signal(self.bits)
        self.rdy = Signal()
        self.tx = Signal(unsigned(8))
        self.tx_rdy = Signal()
        self.tx_trg = Signal()
        self.idx = Signal(8)
        self.latch = Signal()

        # statistics
        self.n_transmitted = Signal(32)
        self.n_transmitted_latched = Signal(32)

        self.ports = [
            self.fifo_rdy,
            self.rdy,
            self.tx,
            self.tx_rdy,
            self.tx_trg
        ]

    def elaborate(self, platform):
        m = Module()

        data = Signal(self.bits)
        idx = Signal(8)
        pos = Signal(range(self.n_bytes + 1))

        with m.FSM(reset="IDLE") as fsm:

            m.d.comb += self.tx_trg.eq(fsm.ongoing("ENCODE"))
            m.d.comb += self.rdy.eq(fsm.ongoing("DONE") | fsm.ongoing("IDLE"))

            with m.State("IDLE"):
                m.d.sync += pos.eq(0)
                with m.If(self.fifo_rdy == 1):
                    m.d.sync += [
                        data.eq(self.fifo_r_data),
                        idx.eq(self.idx)
                    ]
                    m.next = "ENCODE"

            with m.State("ENCODE"):
                m.next = "WAIT_TX"
                with m.If(pos == 0):
                    m.d.sync += [
                        self.tx.eq(idx),
                    ]
                with m.Elif((pos > 0) & (pos < (self.n_bytes - 1))):
                    m.d.sync += [
                        self.tx.eq(data),
                        data.eq(data >> 8)
                    ]
                with m.Elif(pos == (self.n_bytes - 1)):
                    m.d.sync += [
                        self.tx.eq(0xff)
                    ]

            with m.State("WAIT_TX"):
                with m.If(self.tx_rdy == 1):
                    with m.If(pos != (self.n_bytes - 1)):
                        m.d.sync += pos.eq(pos + 1)
                        m.next = "ENCODE"
                    with m.Else():
                        m.next = "DONE"

            with m.State("DONE"):
                m.d.sync += self.n_transmitted.eq(self.n_transmitted + 1)
                m.next = "IDLE"

        # Latch counter
        with m.If(self.latch == 1):
            m.d.sync += self.n_transmitted_latched.eq(self.n_transmitted)

        return m

if __name__ == '__main__':
    dut = HitSerialiser(bits=48, n_bytes=8)

    sim = Simulator(dut)

    def wait_convert():
        for i in range(10):
            yield

    def mimic_tx_rdy():
        for i in range(10):
            yield
        yield dut.tx_rdy.eq(1)
        yield
        yield dut.tx_rdy.eq(0)
        yield

    def transmit():
        yield dut.fifo_rdy.eq(1)
        yield
        yield dut.fifo_rdy.eq(0)
        yield
        for i in range(8):
            yield from wait_convert()
            yield from mimic_tx_rdy()

    def write(word):
        yield dut.fifo_r_data.eq(word)
        yield
        yield from transmit()

    def check_init():
        yield
        assert(yield dut.rdy == 1)
        for i in range(10):
            yield

    def check_write():
        yield dut.idx.eq(0xBA)
        yield from write(0x4)
        yield from write(0x0a)
        yield from write(0xfe)
        yield dut.idx.eq(0xCD)
        yield from write(0x1337)
        yield from write(0x133713)
        yield from write(0x13371337)
        yield from write(0xab13371337)
        yield from write(0xabcd13371337)
        for i in range(200):
            yield

    def proc():
        yield from check_init()
        yield from check_write()

    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('hitser.vcd', 'hitser_orig.gtkw', traces=dut.ports):
        sim.run()
