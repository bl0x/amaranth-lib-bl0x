from amaranth import *
from amaranth.sim import *

class EdgeDetector(Elaboratable):
    def __init__(self):
        self.input = Signal()
        self.rose = Signal()
        self.fell = Signal()

        self.ports = [
                self.input,
                self.rose,
                self.fell
                ]

    def elaborate(self, platform):
        m = Module()

        prev = Signal()

        m.d.sync += prev.eq(self.input)
        m.d.comb += [
                self.rose.eq((self.input == 1) & (prev == 0)),
                self.fell.eq((self.input == 0) & (prev == 1))
                ]

        return m

if __name__ == '__main__':
    dut = EdgeDetector()
    sim = Simulator(dut)

    def tick():
        yield Tick()

    def proc():
        assert((yield dut.rose) == 0)
        assert((yield dut.fell) == 0)
        yield dut.input.eq(1)
        yield from tick()
        assert((yield dut.rose) == 1)
        assert((yield dut.fell) == 0)
        yield from tick()
        assert((yield dut.rose) == 0)
        assert((yield dut.fell) == 0)
        yield dut.input.eq(0)
        yield from tick()
        assert((yield dut.rose) == 0)
        assert((yield dut.fell) == 1)
        yield from tick()
        assert((yield dut.rose) == 0)
        assert((yield dut.fell) == 0)

    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('edge_detect.vcd', 'edge_detect.gtkw', traces=dut.ports):
        sim.run()

