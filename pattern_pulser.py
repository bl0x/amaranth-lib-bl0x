from amaranth import *
from amaranth.sim import *

class PatternPulser(Elaboratable):

    def __init__(self):
        self.out = Signal()
        self.step = Signal(5)

        self.ports = (self.out, self.step)

    def elaborate(self, platform):

        len_ctr = Signal(8, reset=1)
        increment = Signal(8, reset=1)
        cycle_ctr = Signal(8)

        m = Module()

        with m.If(cycle_ctr == 0xff):
            m.d.sync += len_ctr.eq(len_ctr + increment)
            with m.If(len_ctr + increment > 0xff):
                with m.If(increment == 0x80):
                    m.d.sync += increment.eq(1)
                with m.Else():
                    m.d.sync += increment.eq(increment * 2)


        m.d.sync += cycle_ctr.eq(cycle_ctr + 1)

        m.d.comb += [
            self.step.eq(increment),
            self.out.eq(cycle_ctr <= len_ctr)
        ]

        return m

if __name__ == '__main__':
    dut = PatternPulser()

    sim = Simulator(dut)
    def proc():
        for i in range(256*256*3):
            yield

    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('pattern_pulser.vcd', 'pattern_pulser.gtkw',
                       traces=dut.ports):
        sim.run()
