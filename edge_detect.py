from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.sim import *

class EdgeDetector(wiring.Component):

    i: In(1)
    rose: Out(1)
    fell: Out(1)

    def elaborate(self, platform):
        m = Module()

        prev = Signal()

        m.d.sync += prev.eq(self.i)
        m.d.comb += [
            self.rose.eq((self.i == 1) & (prev == 0)),
            self.fell.eq((self.i == 0) & (prev == 1))
        ]

        return m

if __name__ == '__main__':
    dut = EdgeDetector()
    sim = Simulator(dut)

    def proc():
        assert((yield dut.rose) == 0)
        assert((yield dut.fell) == 0)
        yield dut.i.eq(1)
        yield
        assert((yield dut.rose) == 1)
        assert((yield dut.fell) == 0)
        yield
        assert((yield dut.rose) == 0)
        assert((yield dut.fell) == 0)
        yield dut.i.eq(0)
        yield
        assert((yield dut.rose) == 0)
        assert((yield dut.fell) == 1)
        yield
        assert((yield dut.rose) == 0)
        assert((yield dut.fell) == 0)

    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('edge_detect.vcd', 'edge_detect.gtkw'):
        sim.run()

