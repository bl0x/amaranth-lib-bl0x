from amaranth import *
from amaranth.sim import *
from amaranth.lib.fifo import AsyncFIFO

from tdc import Tdc
from tdc_to_hit import TdcToHit

class TestTdcFifoHit(Elaboratable):

    def __init__(self):
        # in
        self.input = Signal()
        self.time = Signal(32)
        # out
        self.output = Signal(32)
        self.counter = Signal(16)

    def elaborate(self, platform):

        tdc = Tdc()
        fifo = AsyncFIFO(width=38, depth=16, w_domain="fast", r_domain="sync")
        tdc2hit = TdcToHit()

        m = Module()

        m.d.comb += [
                tdc.input.eq(self.input),
                tdc.time.eq(self.time),
                fifo.w_data.eq(tdc.output),
                fifo.w_en.eq(tdc.rdy),
                tdc2hit.input.eq(fifo.r_data),
                self.output.eq(tdc2hit.output),
                self.counter.eq(tdc2hit.counter_rise)
                ]

        with m.If(fifo.r_rdy == 1):
            m.d.sync += fifo.r_en.eq(1)
        with m.Else():
            m.d.sync += fifo.r_en.eq(0)

        m.submodules.tdc = tdc
        m.submodules.fifo = fifo
        m.submodules.tdc2hit = tdc2hit

        return m

if __name__ == "__main__":
    dut = TestTdcFifoHit()
    i0 = Signal()
    t = Signal(32)
    out = Signal(32)
    counter = Signal(16)

    m = Module()
    m.domains += ClockDomain("sync")
    m.domains += ClockDomain("fast")
    m.submodules.dut = dut

    m.d.comb += [
        dut.input.eq(i0),
        dut.time.eq(t),
        out.eq(dut.output),
        counter.eq(dut.counter)
    ]

    sim = Simulator(m)

    stop = 50

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

    sim.add_clock(1/200e6)
    sim.add_clock(1/100e6, domain="fast")
    sim.add_clock(1/100e6, phase=(1/100e6)/4, domain="fast_90")
    sim.add_sync_process(proc)
    sim.add_sync_process(time)
    sim.add_sync_process(input)
    with sim.write_vcd("tdc_fifo_hit.vcd", "tdc_fifo_hit_orig.gtkw"):
        sim.run()
