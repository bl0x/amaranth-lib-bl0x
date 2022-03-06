from amaranth import *
from amaranth.sim import *

from edge_to_pulse import EdgeToPulse

class Blinker(Elaboratable):
    def __init__(self, width=10000):
        self.go = Signal()
        self.counter = Signal(unsigned(8))
        self.output = Signal()
        self.width = width

    def elaborate(self, platform):
        ed = EdgeToPulse(width=self.width)
        count = Signal(unsigned(8))

        m = Module()

        m.d.comb += self.output.eq(ed.output)

        with m.If((self.go == 1)):
            m.d.sync += [
                    count.eq(self.counter)
            ]

        with m.If((count > 0) & (ed.output == 0)) as blinker:
            m.d.sync += [
                count.eq(count - 1),
                ed.input.eq(1)
            ]
        with m.Else():
            m.d.sync += [
                ed.input.eq(0)
            ]

        m.submodules.edge_to_pulse = ed

        return m

if __name__ == "__main__":
    dut = Blinker(width = 5)
    sim = Simulator(dut)

    def strobe():
        yield dut.go.eq(1)
        yield
        yield dut.go.eq(0)
        yield

    def proc():
        assert((yield dut.output) == 0)
        yield
        yield dut.counter.eq(4)
        yield dut.go.eq(1)
        yield
        yield
        yield dut.go.eq(0)
        yield
        assert((yield dut.output) == 1)
        yield
        yield
        yield
        yield
        yield
        assert((yield dut.output) == 0)
        for i in range(30):
            yield

    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('blinker.vcd', 'blinker_orig.gtkw'):
        sim.run()
