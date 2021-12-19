from amaranth import *
from amaranth.sim import *

class Pulser(Elaboratable):

    def __init__(self, period=10, length=1):
        self.period = Signal(range(1, 10000000), reset=period)
        self.length = Signal(range(1, 10000000), reset=length)
        self.out = Signal()

        self.ports = (
                self.period,
                self.length,
                self.out
                )

    def elaborate(self, platform):
        counter = Signal(range(0, 10000000), reset=0)
        m = Module()

        with m.If(counter == 0):
            m.d.sync += counter.eq(self.period - 1)
        with m.Else():
            m.d.sync += counter.eq(counter - 1)

        with m.If(counter < self.length):
            m.d.sync += self.out.eq(1)
        with m.Else():
            m.d.sync += self.out.eq(0)

        return m

if __name__ == '__main__':
    dut = Pulser(period=10, length=3)

    sim = Simulator(dut)
    def proc():
        for i in range(200):
            yield Tick()
            yield Settle()

    sim.add_clock(1e-6)
    sim.add_sync_process(proc)
    with sim.write_vcd('pulser.vcd', 'pulser.gtkw', traces=dut.ports):
        sim.run()
