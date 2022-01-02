from amaranth import *
from amaranth.sim import *
from amaranth.lib.fifo import *

from generic.oversampling_input import OversamplingInput

# output format:
# | falling | rising | time | sample |
# |---------|--------|------|--------|
# |    37   |   36   | 35 4 | 3    0 |

class Tdc(Elaboratable):
    def __init__(self):
        # in
        self.clk_0 = Signal()
        self.clk_90 = Signal()
        self.input = Signal()
        self.time = Signal(32)
        # out
        self.output = Signal(38)
        self.rdy = Signal()

    def elaborate(self, platform):

        sample = Signal(4)
        falling = Signal()
        rising = Signal()
        stable_on = Signal()
        stable_off = Signal()
        prev_last = Signal()

        os_in = OversamplingInput()

        m = Module()

        m.domains += [
                ClockDomain("fast")
                ]

        m.d.comb += [
                ClockSignal("fast").eq(self.clk_0)
                ]

        m.d.comb += [
                os_in.clk_0.eq(self.clk_0),
                os_in.clk_90.eq(self.clk_90),
                os_in.input.eq(self.input),
                sample.eq(os_in.data4),
                stable_on.eq(os_in.data4 == 15),
                stable_off.eq(os_in.data4 == 0),
                falling.eq(((prev_last == 1) & (os_in.data4[0] == 0))
                    | (os_in.data4[2:4] == C(1, 2))
                    | (os_in.data4[1:3] == C(1, 2))
                    | (os_in.data4[0:2] == C(1, 2))),
                rising.eq(((prev_last == 0) & (os_in.data4[0] == 1))
                    | (os_in.data4[2:4] == C(2, 2))
                    | (os_in.data4[1:3] == C(2, 2))
                    | (os_in.data4[0:2] == C(2, 2)))
                ]

        with m.If((falling == 1) | (rising == 1)):
            # falling edge
            m.d.fast += [
                self.output.eq(Cat(Cat(Cat(sample, self.time), rising), falling))
                ]
        with m.Else():
            # No change
            m.d.fast += [
                self.output.eq(C(0, unsigned(37)))
                ]

        m.d.fast += [
                prev_last.eq(sample[3])
                ]

        m.submodules += os_in
        return m

if __name__ == "__main__":
    dut = Tdc()
    fifo = AsyncFIFO(width=16, depth=8)
    clk_0 = Signal()
    clk_90 = Signal()
    i0 = Signal()
    t = Signal(32)
    out = Signal(38)

    m = Module()
    m.domains += ClockDomain("sync")
    m.submodules += [dut, fifo]

    m.d.comb += [
            dut.clk_0.eq(clk_0),
            dut.clk_90.eq(clk_90),
            dut.input.eq(i0),
            dut.time.eq(t),
            out.eq(dut.output)
            ]

    sim = Simulator(m)

    stop = 50

    def time():
        for i in range(stop):
            yield t.eq(t + 1)
            yield

    def clocks():
        for i in range(stop):
            yield clk_0.eq(~clk_0)
            yield Delay(1/40e6)
            yield clk_90.eq(~clk_90)
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



    sim.add_clock(1/20e6)
    sim.add_sync_process(proc)
    sim.add_sync_process(time)
    sim.add_sync_process(clocks)
    sim.add_sync_process(input)
    with sim.write_vcd("tdc.vcd", "tdc.gtkw"):
        sim.run()
