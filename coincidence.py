from amaranth import *
from amaranth.sim import *

# Note:
# Make sure, that the input does not change faster than the size of the
# coincidence window.

class Coincidence(Elaboratable):
    def __init__(self, bits_time=32, bits_data=16):
        # Configuration
        self.bits_time = bits_time
        self.bits_data = bits_data

        # Inputs
        self.t0 = Signal(bits_time + 1) # signed (MSB always 0)
        self.t1 = Signal(bits_time + 1) # signed (MSB always 0)
        self.d0 = Signal(bits_data)
        self.d1 = Signal(bits_data)

        # Outputs
        self.diff = Signal.like(self.t0) # signed
        self.new_diff_pulse = Signal()   # 1 whenever diff changed
        self.out = Signal()              # 1 whenever coincidence is true
        self.out_pulse = Signal()        # 1 whenever a new value leads to
                                         # a true coincidence

        # Variables
        self.window_min = Signal(8)
        self.window_max = Signal(8)

    def elaborate(self, platform):
        m = Module()

        t0_greater = Signal()
        t0 = self.t0
        t1 = self.t1
        diff = self.diff

        t0_prev = Signal.like(t0)
        t1_prev = Signal.like(t1)

        new_value_t0 = Signal()
        new_value_t1 = Signal()
        new_value = Signal()

        # Save the previous value
        m.d.sync += [
            t0_prev.eq(t0),
            t1_prev.eq(t1)
        ]

        # Check, if anything changed on the inputs
        m.d.comb += [
            new_value_t0.eq(t0 != t0_prev),
            new_value_t1.eq(t1 != t1_prev),
            new_value.eq(new_value_t0 | new_value_t1)
        ]

        # Calculate difference and coincidence condition
        m.d.comb += [
            self.diff.eq(t0.as_signed() - t1.as_signed()),
            self.out.eq((diff.as_signed() < self.window_max.as_signed())
                        & (diff.as_signed() >= self.window_min.as_signed()))
        ]

        # Output pulses
        # new_diff_pulse is pulsed on every new value,
        # out_pulse, also the coincidence is true
        m.d.comb += [
            self.new_diff_pulse.eq(new_value),
            self.out_pulse.eq(self.out & new_value)
        ]

        return m


if __name__ == "__main__":
    dut = Coincidence()
    sim = Simulator(dut)

    def proc():
        yield dut.window_min.eq(-20)
        yield dut.window_max.eq(50)
        yield dut.t0.eq(1000)
        yield dut.t1.eq(800)
        yield
        yield
        yield
        yield dut.t1.eq(1100)
        yield
        yield
        yield
        yield dut.t0.eq(1080)
        yield
        yield
        yield
        yield dut.t0.eq(1100)
        yield
        yield
        yield
        yield dut.t0.eq(1110)
        yield
        yield
        yield
        yield dut.t0.eq(1150)
        yield
        yield
        yield
        yield dut.t0.eq(1200)
        yield
        yield
        yield
        yield dut.t1.eq(1200+20)
        yield
        yield
        yield

    sim.add_clock(1/12e6)
    sim.add_sync_process(proc)

    with sim.write_vcd("coincidence.vcd", "coincidence_orig.gtkw"):
        sim.run()
