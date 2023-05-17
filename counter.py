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
        self.count_latched = Signal(unsigned(bits))
        self.latch = Signal()

        self.ports = [
            self.input,
            self.count,
            self.count_latched,
            self.latch
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

        with m.If(self.latch == 1):
            m.d.sync += self.count_latched.eq(self.count)

        m.submodules.ed = ed
        return m

class CounterSync(Elaboratable):
    def __init__(self, name, bits):
        self.bits = bits

        self.counter = Counter(bits=self.bits)
        self.counter_s = Signal.like(self.counter.count)
        self.counter_ffs = FFSynchronizer(self.counter.count, self.counter_s,
                                          o_domain="sync")

    def connect(self, _input, latch, output, latched_output):
        return [
            self.counter.input.eq(_input),
            counter.latch.eq(latch),
            output.eq(counter_s),
            latched_output.eq(counter.count_latched),
        ]

    def elaborate(self, platform):
        m = Module()
        m.submodules["counter_"+name] = self.counter
        m.submodules["counter_ffs_"+name] = self.counter_ffs
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
        assert((yield dut.count_latched) == 0)

        yield dut.latch.eq(1)
        yield
        yield dut.latch.eq(0)
        yield
        assert((yield dut.count_latched) == 21)

    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('counter.vcd', 'counter.gtkw', traces=dut.ports):
        sim.run()


