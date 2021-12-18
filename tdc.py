from nmigen import *
from nmigen.sim import *
from nmigen.lib.fifo import *

from generic.oversampling_input import OversamplingInput

class Tdc(Elaboratable):
    def __init__(self):
        self.clk_0 = Signal()
        self.clk_90 = Signal()
        self.input = Signal()
        self.time = Signal(32)
        self.output = Signal(16)
        self.w_en = Signal()

    def elaborate(self, platform):

        sample = Signal(4)

        os_in = OversamplingInput()

        m = Module()

        m.d.comb += [
                os_in.clk_0.eq(self.clk_0),
                os_in.clk_90.eq(self.clk_90),
                os_in.input.eq(self.input),
                sample.eq(os_in.data4),
                ]



        m.submodules += os_in
        return m

if __name__ == "__main__":
    dut = Tdc()
    fifo = AsyncFIFO(width=16, depth=8)
    clk_0 = Signal()
    clk_90 = Signal()
    i0 = Signal()

    m = Module()
    m.domains += ClockDomain("sync")
    m.submodules += [dut, fifo]

    m.d.comb += [
            dut.clk_0.eq(clk_0),
            dut.clk_90.eq(clk_90),
            dut.input.eq(i0),
            fifo.w_data.eq(dut.output),
            fifo.w_en.eq(dut.w_en),
            ]

    sim = Simulator(m)

    def proc():
        yield

    sim.add_clock(1/20e6)
    sim.add_sync_process(proc)
    with sim.write_vcd("tdc.vcd", "tdc.gtkw"):
        sim.run()
