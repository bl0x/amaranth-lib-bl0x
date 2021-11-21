from nmigen import *
from nmigen.sim import *
import math

# double dabble algorithm
# see e.g.: https://en.wikipedia.org/wiki/Double_dabble

class BinToBcd(Elaboratable):
    def __init__(self, bits=8):
        self.bin_bits = bits
        self.digits = math.ceil(self.bin_bits / 3)
        self.bcd_bits = 4 * self.digits
        self.mem = Signal(self.bin_bits + self.bcd_bits)

        self.bin = Signal(self.bin_bits)
        self.bcd = Signal(self.bcd_bits)
        self.trg = Signal()
        self.rdy = Signal()

        self.ports = [
                self.bin,
                self.bcd,
                self.trg,
                self.rdy
                ]

    def elaborate(self, platform):
        m = Module()

        iteration = Signal(unsigned(4))
        digit = Signal(unsigned(4))

        with m.FSM(reset="IDLE"):
            with m.State("IDLE"):
                with m.If(self.trg == 1):
                    m.d.sync += [
                            self.mem[0:self.bin_bits].eq(self.bin),
                            self.mem[self.bin_bits:].eq(0),
                            iteration.eq(self.bin_bits),
                            self.rdy.eq(0),
                            digit.eq(0)
                            ]
                    m.next = "ADD"

            with m.State("ADD"):
                mem = self.mem.bit_select(self.bin_bits + digit * 4, 4)
                m.d.sync += [
                        digit.eq(digit + 1)
                        ]
                with m.If(mem > 4):
                    m.d.sync += [
                            mem.eq(mem + 3)
                            ]

                with m.If(digit == self.digits):
                    m.next = "SHIFT"

            with m.State("SHIFT"):
                m.d.sync += [
                        self.mem.eq(self.mem.shift_left(1)),
                        iteration.eq(iteration - 1),
                        digit.eq(0)
                        ]
                with m.If(iteration == 1):
                    m.next = "DONE"
                with m.Else():
                    m.next = "ADD"

            with m.State("DONE"):
                m.d.sync += [
                        self.rdy.eq(1)
                        ]
                m.next = "IDLE"

        m.d.comb += self.bcd.eq(self.mem[self.bin_bits:])

        return m

if __name__ == '__main__':
    dut = BinToBcd(bits=8)

    sim = Simulator(dut)

    def tick():
        yield Tick()
        yield Settle()

    def test_int(n, bcd):
        yield dut.bin.eq(n)
        yield dut.trg.eq(1)
        yield from tick()
        yield dut.trg.eq(0)
        while True:
            yield from tick()
            if (yield dut.rdy) == 1:
                break
        yield from tick()

        assert((yield dut.bcd) == bcd)

    def proc():
        yield from test_int(9, 0x9)
        yield from test_int(42, 0x42)
        yield from test_int(255, 0x255)

    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('bintobcd.vcd', 'bintobcd.gtkw', traces=dut.ports):
        sim.run()
