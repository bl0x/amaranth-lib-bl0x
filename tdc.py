from amaranth import *
from amaranth.sim import *

from generic.oversampling_input import OversamplingInput

# output format:
# | falling | rising | time | sample |
# |---------|--------|------|--------|
# |    37   |   36   | 35 4 | 3    0 |

class Tdc(Elaboratable):
    def __init__(self, name, domain="fast", domain_90="fast_90"):
        # in
        self.clk_0 = ClockSignal(domain)
        self.clk_90 = ClockSignal(domain_90)
        self.input = Signal()
        self.time = Signal(32)
        self.name = name
        # out
        self.output = Signal(38)
        self.rdy = Signal()

        self._domain = domain
        self._domain_90 = domain_90

        # internal
        self.sample = Signal(4)
        self.falling = Signal()
        self.rising = Signal()
        self.stable_on = Signal()
        self.stable_off = Signal()
        self.prev_last = Signal()

    def connect_to_oversampling_input(self, os_in):
        return [
                os_in.clk_0.eq(self.clk_0),
                os_in.clk_90.eq(self.clk_90),
                os_in.input.eq(self.input),
                self.sample.eq(os_in.data4),
                self.stable_on.eq(os_in.data4 == 15),
                self.stable_off.eq(os_in.data4 == 0),
                self.falling.eq(((self.prev_last == 1) & (os_in.data4[0] == 0))
                    | (os_in.data4[2:4] == C(1, 2))
                    | (os_in.data4[1:3] == C(1, 2))
                    | (os_in.data4[0:2] == C(1, 2))),
                self.rising.eq(((self.prev_last == 0) & (os_in.data4[0] == 1))
                    | (os_in.data4[2:4] == C(2, 2))
                    | (os_in.data4[1:3] == C(2, 2))
                    | (os_in.data4[0:2] == C(2, 2)))
                ]

    def elaborate(self, platform):

        os_in = OversamplingInput(self.name)

        m = Module()

        m.d.comb += self.connect_to_oversampling_input(os_in)

        with m.If((self.falling == 1) | (self.rising == 1)):
            # falling edge
            m.d[self._domain] += [
                    self.output.eq(Cat(Cat(Cat(self.sample,
                        self.time), self.rising), self.falling)),
                    self.rdy.eq(1)
                    ]

        with m.Else():
            # No change
            m.d[self._domain] += [
                    self.output.eq(C(0, unsigned(37))),
                    self.rdy.eq(0)
                    ]

        m.d[self._domain] += self.prev_last.eq(self.sample[3])

        m.submodules.os_in = os_in
        return m

if __name__ == "__main__":
    dut = Tdc("test")
    i0 = Signal()
    t = Signal(32)
    out = Signal(38)

    m = Module()
    m.domains += ClockDomain("fast")
    m.domains += ClockDomain("fast_90")
    m.domains += ClockDomain("sync")
    m.domains += ClockDomain("what")
    m.submodules.dut = dut

    m.d.comb += [
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
        for i in range(5):
            yield from pulse(i)
            yield from pause(5)


    sim.add_clock(1/10e6, domain="what")
    sim.add_clock(1/1e6, domain="fast")
    sim.add_clock(1/1e6, phase=(1/1e6)/4, domain="fast_90")
    sim.add_sync_process(time, domain="fast")

    sim.add_clock(1/1e6)
    sim.add_sync_process(proc)
    sim.add_sync_process(input)

    with sim.write_vcd("tdc.vcd", "tdc.gtkw"):
        sim.run()
