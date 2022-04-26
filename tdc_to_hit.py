from amaranth import *
from amaranth.sim import *

from counter import Counter

# Transforms 38-bit output from a Tdc into hit data of the form:
#
# | Timestamp | Length of pulse |
# |-----------|-----------------|
# |31       16|15              0|
#
# Unit of length of pulse is governed by the 'resolution' parameter

class SampleToVal(Elaboratable):
    def __init__(self):
        # in
        self.sample = Signal(4)
        # out
        self.value = Signal(2)

    def elaborate(self, platform):

        m = Module()

        with m.If(self.sample[0] == 1):
            m.d.comb += self.value.eq(0)
        with m.Elif(self.sample[1] == 1):
            m.d.comb += self.value.eq(1)
        with m.Elif(self.sample[2] == 1):
            m.d.comb += self.value.eq(2)
        with m.Elif(self.sample[3] == 1):
            m.d.comb += self.value.eq(3)
        with m.Else():
            m.d.comb += self.value.eq(0)

        return m

RISING_IS_START = 0
FALLING_IS_START = 1

class TdcToHit(Elaboratable):

    def __init__(self):
        # in
        self.input = Signal(38)
        self.polarity = Signal()
        self.busy = Signal()
        self.strobe = Signal()
        # out
        self.output = Signal(32)
        self.rdy = Signal()
        self.rdy_pulse = Signal()
        self.counter_rise = Signal(16)
        self.counter_fall = Signal(16)

    def is_rising(self):
        return self.input[36] == 1

    def is_falling(self):
        return self.input[37] == 1

    def elaborate(self, platform):

        prev = Signal(32)
        start = Signal(32)
        fine_start = Signal(2)
        fine_end = Signal(2)
        end = Signal(36)
        time = Signal(16)
        diff = Signal(32 + 2) # nanoseconds
        diff2 = Signal(16)
        new_signal = Signal()

        s2v = SampleToVal()
        count_rise = Counter()
        count_fall = Counter()

        m = Module()

        m.d.comb += [
            count_rise.input.eq(self.input[36]),
            count_fall.input.eq(self.input[37]),
            self.counter_rise.eq(count_rise.count),
            self.counter_fall.eq(count_fall.count),
        ]

        m.d.sync += prev.eq(self.input[4:36])
        with m.If(prev != self.input[4:36]):
            m.d.sync += new_signal.eq(1)
        with m.Else():
            m.d.sync += new_signal.eq(0)

        with m.If(self.is_falling()):
            m.d.comb += s2v.sample.eq(~self.input[0:4])
        with m.Elif(self.is_rising()):
            m.d.comb += s2v.sample.eq(self.input[0:4])

        with m.FSM(reset="RESET") as start_stop:
            with m.State("RESET"):
                m.d.sync += [
                    new_signal.eq(0),
                    self.rdy.eq(0),
                    self.rdy_pulse.eq(0),
                    self.busy.eq(0)
                ]
                m.next = "WAIT_START"

            with m.State("WAIT_START"):
                with m.If(self.polarity == RISING_IS_START):
                    with m.If(self.is_rising()):
                        m.d.sync += [
                            start.eq(self.input[4:4+32]),
                            fine_start.eq(s2v.value),
                            time.eq(self.input[4:4+16])
                        ]
                        m.next = "WAIT_END"
                with m.Elif(self.polarity == FALLING_IS_START):
                    with m.If(self.is_falling()):
                        m.d.sync += [
                            start.eq(self.input[4:4+32]),
                            fine_start.eq(s2v.value),
                            time.eq(self.input[4:4+16])
                        ]
                        m.next = "WAIT_END"

            with m.State("WAIT_END"):
                with m.If(self.polarity == RISING_IS_START):
                    with m.If(self.is_falling()):
                        m.d.sync += [
                            end.eq(self.input[0:36]),
                            fine_end.eq(s2v.value),
                            diff.eq(self.input[4:4+32] - start),
                            self.busy.eq(1)
                        ]
                        m.next = "READY_PULSE"
                with m.Elif(self.polarity == FALLING_IS_START):
                    with m.If(self.is_rising()):
                        m.d.sync += [
                            end.eq(self.input[0:36]),
                            fine_end.eq(s2v.value),
                            diff.eq(self.input[4:4+32] - start),
                            self.busy.eq(1)
                        ]
                        m.next = "READY_PULSE"
            with m.State("READY_PULSE"):
                m.d.sync += [
                    self.busy.eq(0),
                    self.rdy.eq(1),
                    self.rdy_pulse.eq(1)
                ]
                m.next = "RESET"
            with m.State("WAIT_STROBE"):
                m.d.sync += self.rdy_pulse.eq(0)
                with m.If(self.strobe == 1):
                    m.next = "RESET"

        m.d.comb += [
            diff2.eq(
                Mux(diff < 0x3fff, (diff << 2) + fine_end - fine_start, 0xffff)
            )
        ]
        m.d.sync += [
            self.output.eq(Cat(diff2, time))
        ]

        m.submodules.s2v = s2v
        m.submodules.count_rise = count_rise
        m.submodules.count_fall = count_fall

        return m

if __name__ == "__main__":
    dut = TdcToHit()
    dut2 = SampleToVal()

    m = Module()
    m.submodules.dut_tdc = dut
    m.submodules.dut_s2v = dut2

    sim = Simulator(m)

    def test_tdc2hit():
        yield dut.polarity.eq(RISING_IS_START)
        yield dut.input.eq((1 << 36) | (15 << 4) | 0b1110) # rising, sample = 1
        assert((yield dut.counter_rise) == 0)
        assert((yield dut.counter_fall) == 0)
        yield
        assert dut.output.eq(0)
        yield dut.input.eq((1 << 37) | (16 << 4) | 0b0011) # falling, sample = 1
        yield
        assert((yield dut.counter_rise) == 1)
        assert((yield dut.counter_fall) == 0)
        yield
        assert((yield dut.output) == (0b1111 << 16) | 5)
        assert((yield dut.counter_rise) == 1)
        assert((yield dut.counter_fall) == 1)
        assert((yield dut.rdy) == 1)
        yield
        assert((yield dut.rdy) == 0)

    def test_s2v():
        yield dut2.sample.eq(0)
        yield
        assert((yield dut2.value) == 0)
        yield dut2.sample.eq(0b0001)
        yield
        assert((yield dut2.value) == 0)
        yield dut2.sample.eq(0b0010)
        yield
        assert((yield dut2.value) == 1)
        yield dut2.sample.eq(0b0100)
        yield
        assert((yield dut2.value) == 2)
        yield dut2.sample.eq(0b1000)
        yield
        assert((yield dut2.value) == 3)

    sim.add_clock(1/20e6)
    sim.add_sync_process(test_s2v)
    sim.add_sync_process(test_tdc2hit)

    with sim.write_vcd("tdc_to_hit.vcd", "tdc_to_hit.gtkw"):
        sim.run()
