from amaranth import *
from amaranth.sim import *

from edge_detect import EdgeDetector

class Counter(Elaboratable):
    def __init__(self, bits=16, rising=True, falling=False):
        self.rising = rising
        self.falling = falling
        self.bits = bits
        self.input = Signal()
        self.count = Signal(unsigned(bits))

        self.ports = [
                self.input,
                self.count
                ]

    def elaborate(self, platform):

        ed = EdgeDetector()

        m = Module()
        m.d.comb += ed.input.eq(self.input)

        if self.rising == True:
            with m.If(ed.rose == 1):
                m.d.sync += self.count.eq(self.count + 1)
        if self.falling == True:
            with m.If(ed.fell == 1):
                m.d.sync += self.count.eq(self.count + 1)

        m.submodules.ed = ed
        return m

if __name__ == '__main__':
    dut = Counter()
    sim = Simulator(dut)

    def strobe():
        yield dut.input.eq(1)
        yield
        yield dut.input.eq(0)
        yield

    def proc():
        assert((yield dut.count) == 0)
        yield
        yield
        yield
        yield dut.input.eq(1)
        yield
        yield
        assert((yield dut.count) == 1)
        yield dut.input.eq(0)
        yield
        yield
        assert((yield dut.count) == 1)

        for i in range(10 * 2):
            yield from strobe()

        assert((yield dut.count) == 21)

    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('counter.vcd', 'counter.gtkw', traces=dut.ports):
        sim.run()


