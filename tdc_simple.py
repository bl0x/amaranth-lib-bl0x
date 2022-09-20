from amaranth import *
from amaranth.sim import *

# output format:
# | falling | rising | time |
# |---------|--------|------|
# |    33   |   32   | 31 0 |

class TdcSimple(Elaboratable):
    def __init__(self, name, domain="fast"):
        # in
        self.clk = ClockSignal(domain)
        self.enable = Signal()
        self.input = Signal()
        self.time = Signal(32)
        self.name = name

        # out
        self.output = Signal(34)
        self.rdy = Signal()

        self._domain = domain

        # internal
        self.sample = Signal()
        self.falling = Signal()
        self.rising = Signal()
        self.prev = Signal()

    def elaborate(self, platform):

        m = Module()

        
        with m.If(self.enable == 1):
            m.d[self._domain] += [
                self.sample.eq(self.input),
                self.prev.eq(self.sample)
            ]
        with m.Else():
            m.d[self._domain] += [
                self.sample.eq(0),
                self.prev.eq(0)
            ]

        m.d.comb += [
            self.falling.eq((self.prev == 1) & (self.sample == 0)),
            self.rising.eq((self.prev == 0) & (self.sample == 1))
        ]

        with m.If((self.falling == 1) | (self.rising == 1)):
            m.d[self._domain] += [
                self.output.eq(Cat(Cat(Cat(self.time), self.rising),
                    self.falling)),
                self.rdy.eq(1)
            ]

        with m.Else():
            m.d[self._domain] += [
                self.output.eq(C(0, unsigned(34))),
                self.rdy.eq(0)
            ]

        return m

if __name__ == "__main__":
    dut = TdcSimple("test")
    i0 = Signal()
    en = Signal()
    t = Signal(32)
    out = Signal(34)

    m = Module()
    m.domains += ClockDomain("fast")
    m.domains += ClockDomain("sync")
    m.domains += ClockDomain("what")
    m.submodules.dut = dut

    m.d.comb += [
        dut.enable.eq(en),
        dut.input.eq(i0),
        dut.time.eq(t),
        out.eq(dut.output)
    ]

    sim = Simulator(m)

    stop = 200

    def time():
        for i in range(stop):
            yield t.eq(t + 1)
            yield

    def proc():
        yield

    def pulse(steps):
        for i in range(steps):
            yield i0.eq(1)
            yield
        yield i0.eq(0)
        yield

    def pause(steps):
        for i in range(steps):
            yield

    def input():
        yield en.eq(0)
        for i in range(5):
            yield from pulse(i)
            yield from pause(5)
        yield en.eq(1)
        for i in range(5):
            yield from pulse(i)
            yield from pause(5)


    sim.add_clock(1/10e6, domain="what")
    sim.add_clock(1/1e6, domain="fast")
    sim.add_sync_process(time, domain="fast")

    sim.add_clock(1/1e6)
    sim.add_sync_process(proc)
    sim.add_sync_process(input)

    with sim.write_vcd("tdc_simple.vcd", "tdc_simple_orig.gtkw"):
        sim.run()
