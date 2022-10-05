from amaranth import *
from amaranth.sim import *

from edge_detect import EdgeDetector

class EdgeToPulse(Elaboratable):
    def __init__(self, bits=16):
        self.width = Signal(bits)
        self.bits = bits

        self.input = Signal()
        self.output = Signal()

        self.ports = [
            self.input,
            self.output
        ]

    def elaborate(self, platform):
        ed = EdgeDetector()
        counter = Signal(self.bits)

        m = Module()

        m.d.comb += ed.input.eq(self.input)

        with m.If(ed.rose == 1):
            m.d.sync += counter.eq(self.width - 1)

        m.d.comb += self.output.eq((ed.rose == 1) | (counter > 0))

        with m.If(counter > 0):
            m.d.sync += counter.eq(counter - 1),

        m.submodules.edge_detector = ed

        return m


if __name__=="__main__":
    dut = EdgeToPulse(width = 2)
    sim = Simulator(dut)

    def strobe():
        yield dut.input.eq(1)
        yield
        yield dut.input.eq(0)
        yield

    def proc():
        assert((yield dut.output) == 0)
        yield
        yield dut.input.eq(1)
        yield
        yield
        assert((yield dut.output) == 1)
        yield dut.input.eq(0)
        yield
        yield
        assert((yield dut.output) == 0)

        for i in range(10 * 2):
            yield from strobe()
            yield

    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('edge_to_pulse.vcd', 'edge_to_pulse_orig.gtkw',
            traces=dut.ports):
        sim.run()
