from amaranth import *
from amaranth.sim import *

class PWM(Elaboratable):

    def __init__(self, bits=8, duty=1):
        self.bits = bits
        self.duty = Signal(bits, reset=duty)
        self.out = Signal()

        self.ports = (
            self.duty,
            self.out
        )

    def elaborate(self, platform):
        counter = Signal(self.bits, reset=0)
        m = Module()

        m.d.sync += counter.eq(counter + 1)

        with m.If(counter < self.duty):
            m.d.sync += self.out.eq(1)
        with m.Else():
            m.d.sync += self.out.eq(0)

        return m

if __name__ == '__main__':
    dut = PWM(bits=8, duty=10)

    sim = Simulator(dut)

    def do():
        for i in range(512):
            yield

    def proc():
        yield from do()
        yield dut.duty.eq(20)
        yield from do()
        yield dut.duty.eq(128)
        yield from do()
        yield dut.duty.eq(1)
        yield from do()

    sim.add_clock(1e-6)
    sim.add_sync_process(proc)
    with sim.write_vcd('pwm.vcd', 'pwm_orig.gtkw', traces=dut.ports):
        sim.run()
