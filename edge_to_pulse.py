from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.sim import *

from edge_detect import EdgeDetector, EdgeDetectorSignature

class EdgeToPulse(wiring.Component):

    o: Out(1)
    i: In(1)
    
    def __init__(self, bits=16):
        self.width = Signal(bits)
        self.bits = bits
        self.ed = EdgeDetector()
        self.io = EdgeDetectorSignature().flip().create()
        super().__init__()

    def elaborate(self, platform):
        counter = Signal(self.bits)

        m = Module()
        ed = m.submodules.edge_detector = self.ed

        wiring.connect(m, self.io, ed.io)

        m.d.comb += self.io.i.eq(self.i)
        m.d.comb += self.o.eq((self.io.rose == 1) | (counter > 0))

        with m.If(self.io.rose == 1):
            m.d.sync += counter.eq(self.width - 1)
        with m.If(counter > 0):
            m.d.sync += counter.eq(counter - 1),

        return m


if __name__=="__main__":
    dut = EdgeToPulse(bits=2)

    def strobe():
        yield dut.i.eq(1)
        yield
        yield dut.i.eq(0)
        yield

    def proc():
        assert((yield dut.o) == 0)
        yield
        yield dut.i.eq(1)
        yield
        yield
        assert((yield dut.o) == 1)
        yield dut.i.eq(0)
        yield
        yield
        yield
        assert((yield dut.o) == 0)

        for i in range(10 * 2):
            yield from strobe()
            yield

    sim = Simulator(dut)
    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('edge_to_pulse.vcd', 'edge_to_pulse_orig.gtkw'):
        sim.run()
