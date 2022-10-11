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

RISING_IS_START = 0
FALLING_IS_START = 1

class TdcToHitSimple(Elaboratable):

    def __init__(self, bits_time=16):
        self.bits_time = bits_time

        # in
        self.input = Signal(32 + 2)
        self.polarity = Signal()
        self.busy = Signal()
        self.strobe = Signal()
        # out
        self.output = Signal(16 + self.bits_time)
        self.rdy = Signal()
        self.rdy_pulse = Signal()
        self.counter_rise = Signal(16)
        self.counter_fall = Signal(16)

    def is_rising(self):
        return self.input[32] == 1

    def is_falling(self):
        return self.input[33] == 1

    def elaborate(self, platform):

        prev = Signal(32)
        start = Signal(32)
        end = Signal(32)
        time = Signal(self.bits_time)
        diff = Signal(32 + 2) # nanoseconds
        diff2 = Signal(16)
        new_signal = Signal()

        end_timeout = Signal(unsigned(self.bits_time))

        count_rise = Counter()
        count_fall = Counter()

        m = Module()

        m.d.comb += [
            count_rise.input.eq(self.input[32]),
            count_fall.input.eq(self.input[33]),
            self.counter_rise.eq(count_rise.count),
            self.counter_fall.eq(count_fall.count),
        ]

        with m.If(end_timeout > 0):
            m.d.sync += end_timeout.eq(end_timeout - 1)

        m.d.sync += prev.eq(self.input)
        with m.If(prev != self.input):
            m.d.sync += new_signal.eq(1)
        with m.Else():
            m.d.sync += new_signal.eq(0)

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
                            start.eq(self.input[0:32]),
                            time.eq(self.input[0:self.bits_time]),
                            end_timeout.eq(-1)
                        ]
                        m.next = "WAIT_END"
                with m.Elif(self.polarity == FALLING_IS_START):
                    with m.If(self.is_falling()):
                        m.d.sync += [
                            start.eq(self.input[0:32]),
                            time.eq(self.input[0:self.bits_time]),
                            end_timeout.eq(-1)
                        ]
                        m.next = "WAIT_END"

            with m.State("WAIT_END"):
                m.d.sync += self.busy.eq(1)
                with m.If(self.polarity == RISING_IS_START):
                    with m.If(self.is_falling()):
                        m.d.sync += [
                            end.eq(self.input[0:32]),
                            diff.eq(self.input[0:32] - start),
                        ]
                        m.next = "READY_PULSE"
                with m.Elif(self.polarity == FALLING_IS_START):
                    with m.If(self.is_rising()):
                        m.d.sync += [
                            end.eq(self.input[0:32]),
                            diff.eq(self.input[0:32] - start),
                        ]
                        m.next = "READY_PULSE"
                with m.If(end_timeout == 0):
                    m.next = "TIMEOUT"

            with m.State("READY_PULSE"):
                m.d.sync += [
                    self.busy.eq(0),
                    self.rdy.eq(1),
                    self.rdy_pulse.eq(1)
                ]
                m.next = "RESET"

            with m.State("TIMEOUT"):
                m.d.sync += self.busy.eq(0)
                m.next = "RESET"

            with m.State("WAIT_STROBE"):
                m.d.sync += self.rdy_pulse.eq(0)
                with m.If(self.strobe == 1):
                    m.next = "RESET"

        m.d.comb += [
            diff2.eq(
                Mux(diff < 0x3fff, diff, 0xffff)
            )
        ]
        m.d.sync += [
            self.output.eq(Cat(diff2, time))
        ]

        m.submodules.count_rise = count_rise
        m.submodules.count_fall = count_fall

        return m

if __name__ == "__main__":
    dut = TdcToHitSimple(bits_time=32)

    m = Module()
    m.submodules.dut_tdc = dut

    sim = Simulator(m)

    def test_tdc2hit():
        time = 0x23232323
        yield dut.polarity.eq(RISING_IS_START)
        yield dut.input.eq((1 << 32) | time) # rising, sample = 1
        assert((yield dut.counter_rise) == 0)
        assert((yield dut.counter_fall) == 0)
        yield
        assert dut.output.eq(0)
        yield dut.input.eq((1 << 33) | time + 1) # falling, sample = 1
        yield
        assert((yield dut.counter_rise) == 1)
        assert((yield dut.counter_fall) == 0)
        yield
        yield
        print("output = {}".format(hex((yield dut.output))))
        assert((yield dut.output) == (time << 16) | 1)
        assert((yield dut.counter_rise) == 1)
        assert((yield dut.counter_fall) == 1)
        assert((yield dut.rdy) == 1)
        yield
        assert((yield dut.rdy) == 0)

    sim.add_clock(1/20e6)
    sim.add_sync_process(test_tdc2hit)

    with sim.write_vcd("tdc_to_hit_simple.vcd", "tdc_to_hit_simple_orig.gtkw"):
        sim.run()
