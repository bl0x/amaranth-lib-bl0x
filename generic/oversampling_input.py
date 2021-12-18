from nmigen import *
from nmigen.sim import *

class OversamplingInput(Elaboratable):
    def __init__(self):
        self.clk_0 = Signal()
        self.clk_90 = Signal()
        self.input = Signal(attrs={"MAXSKEW":"0.5 ns"})
        self.data4 = Signal(4)

        self.ports = [
                self.clk_0,
                self.clk_90,
                self.input,
                self.data4
                ]

    def elaborate(self, platform):

        a = [Signal() for _ in range(4)]
        b = [Signal() for _ in range(4)]
        c = [Signal() for _ in range(4)]
        d = [Signal() for _ in range(4)]

        m = Module()

        m.domains += [
                ClockDomain("p_0"),
                ClockDomain("p_90"),
                ClockDomain("n_0"),
                ClockDomain("n_90")
                ]

        m.d.comb += [
                ClockSignal("p_0").eq(self.clk_0),
                ClockSignal("p_90").eq(self.clk_90),
                ClockSignal("n_0").eq(~self.clk_0),
                ClockSignal("n_90").eq(~self.clk_90),
                ]

        m.d.p_0 += [
                a[0].eq(self.input),
                a[1].eq(a[0]),
                a[2].eq(a[1]),
                a[3].eq(a[2]),

                b[1].eq(b[0]),
                b[2].eq(b[1]),
                b[3].eq(b[2]),

                c[2].eq(c[1]),
                c[3].eq(c[2]),

                d[3].eq(d[2])
                ]

        m.d.p_90 += [
                b[0].eq(self.input),
                c[1].eq(c[0]),
                d[2].eq(d[1])
                ]

        m.d.n_0 += [
                c[0].eq(self.input),
                d[1].eq(d[0])
                ]

        m.d.n_90 += [
                d[0].eq(self.input)
                ]

        m.d.comb += [
                self.data4.eq(Cat(a[3], b[3], c[3], d[3]))
                ]

        return m

if __name__ == "__main__":
    dut = OversamplingInput()
    clk = Signal()
    clk_90 = Signal()
    i0 = Signal()
    o0 = Signal()
    o1 = Signal()
    o2 = Signal()
    o3 = Signal()

    m = Module()
    m.domains += ClockDomain("sync")
    m.submodules += dut

    m.d.comb += [
            dut.clk_0.eq(clk),
            dut.clk_90.eq(clk_90),
            dut.input.eq(i0),
            o0.eq(dut.data4[0]),
            o1.eq(dut.data4[1]),
            o2.eq(dut.data4[2]),
            o3.eq(dut.data4[3]),
            ]

    sim = Simulator(m)

    # clocks
    def proc():
        for i in range(50):
            yield clk.eq(~clk)
            yield Delay(1/40e6)
            yield clk_90.eq(~clk_90)
            yield

    def input():
        yield Delay(205e-9)
        yield i0.eq(1)
        yield Delay(200e-9)
        yield i0.eq(0)
        yield Settle()
        yield Delay(250e-9)
        yield i0.eq(1)
        yield Delay(200e-9)
        yield i0.eq(0)
        yield Settle()
        yield Delay(225e-9)
        yield i0.eq(1)
        yield Delay(200e-9)
        yield i0.eq(0)
        yield Settle()


    sim.add_clock(1/20e6)
    sim.add_sync_process(proc)
    sim.add_process(input)
    with sim.write_vcd('oversampling_input.vcd', 'oversampling_input.gtkw',
            traces=dut.ports + [o0, o1, o2, o3]):
        sim.run()

