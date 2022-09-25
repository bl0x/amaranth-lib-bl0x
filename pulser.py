from amaranth import *
from amaranth.sim import *

SINGLE_PULSE = 0
DOUBLE_PULSE = 1

class Pulser(Elaboratable):

    def __init__(self, period=10, length=1):
        self.period = Signal(range(1, 10000000), reset=period)
        self.length = Signal(range(1, 10000000), reset=length)
        self.length2 = Signal(range(1, 10000000), reset=length)
        self.distance = Signal(range(1, 100000), reset=0)
        self.enable = Signal()
        self.mode = Signal()
        self.out = Signal()
        self.sync = Signal()

        self.ports = (
            self.period,
            self.length,
            self.length2,
            self.enable,
            self.mode,
            self.out,
            self.sync
        )

    def elaborate(self, platform):
        counter = Signal(range(0, 10000000), reset=0)
        m = Module()

        m.d.comb += self.sync.eq(counter == 0)

        with m.If(counter == self.period - 1):
            m.d.sync += counter.eq(0)
        with m.Else():
            m.d.sync += counter.eq(counter + 1)

        with m.If(self.enable == 0):
            m.d.sync += self.out.eq(0)
        with m.Else():
            with m.If((counter < self.length)
                      | (
                          (self.mode == DOUBLE_PULSE)
                          & (counter < self.distance + self.length2)
                          & (counter > self.distance)
                        )
                      ):
                m.d.sync += self.out.eq(1)
            with m.Else():
                m.d.sync += self.out.eq(0)


        return m

if __name__ == '__main__':
    dut = Pulser(period=10, length=3)

    sim = Simulator(dut)
    def proc():
        for i in range(200):
            if (i == 50):
                yield dut.enable.eq(1)
            yield
        yield dut.length.eq(5)
        for i in range(200):
            yield
        yield dut.period.eq(7)
        for i in range(200):
            yield
        yield dut.period.eq(50)
        yield dut.mode.eq(DOUBLE_PULSE)
        yield dut.distance.eq(10)
        yield dut.length2.eq(5)
        yield dut.length.eq(3)
        for i in range(200):
            yield


    sim.add_clock(1e-6)
    sim.add_sync_process(proc)
    with sim.write_vcd('pulser.vcd', 'pulser.gtkw', traces=dut.ports):
        sim.run()
