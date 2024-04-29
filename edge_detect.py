from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.sim import *

class EdgeDetectorSignature(wiring.Signature):
    def __init__(self):
        super().__init__({
            "i": In(1),
            "rose": Out(1),
            "fell": Out(1)
        })

class EdgeDetector(wiring.Component):

    io: In(EdgeDetectorSignature().flip())

    def elaborate(self, platform):
        m = Module()

        prev = Signal()

        m.d.sync += prev.eq(self.io.i)
        m.d.comb += [
            self.io.rose.eq((self.io.i == 1) & (prev == 0)),
            self.io.fell.eq((self.io.i == 0) & (prev == 1))
        ]

        return m

if __name__ == '__main__':
    dut = EdgeDetector()
    sim = Simulator(dut)

    def proc():
        assert((yield dut.io.rose) == 0)
        assert((yield dut.io.fell) == 0)
        yield dut.io.i.eq(1)
        yield
        assert((yield dut.io.rose) == 1)
        assert((yield dut.io.fell) == 0)
        yield
        assert((yield dut.io.rose) == 0)
        assert((yield dut.io.fell) == 0)
        yield dut.io.i.eq(0)
        yield
        assert((yield dut.io.rose) == 0)
        assert((yield dut.io.fell) == 1)
        yield
        assert((yield dut.io.rose) == 0)
        assert((yield dut.io.fell) == 0)

    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('edge_detect.vcd', 'edge_detect.gtkw'):
        sim.run()

