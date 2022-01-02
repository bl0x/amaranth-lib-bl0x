from amaranth import *
from amaranth.sim import *

from tdc import Tdc

# Transforms 38-bit output from a Tdc into hit data of the form:
# Transforms 39-bit output from a Tdc into hit data of the form:
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
        # out
        self.output = Signal(32)
        self.rdy = Signal()

    def elaborate(self, platform):

        start = Signal(36)
        fine_start = Signal(2)
        fine_end = Signal(2)
        end = Signal(36)
        time = Signal(16)
        diff = Signal(16)
        diff2 = Signal(16)

        s2v = SampleToVal()

        m = Module()

        with m.If(self.input[37] == 1):
            m.d.comb += s2v.sample.eq(~self.input[0:4])
        with m.Elif(self.input[36] == 1):
            m.d.comb += s2v.sample.eq(self.input[0:4])

        with m.If(self.polarity == RISING_IS_START):
            with m.If(self.input[36] == 1):
                m.d.sync += [
                        start.eq(self.input[0:36]),
                        fine_start.eq(s2v.value),
                        time.eq(self.input[4:4+16])
                        ]
            with m.Elif(self.input[37] == 1):
                m.d.sync += [
                        end.eq(self.input[0:36]),
                        fine_end.eq(s2v.value),
                        diff[2:].eq(self.input[4:4+32] - start[4:4+32])
                        ]
        with m.Elif(self.polarity == FALLING_IS_START):
            with m.If(self.input[37] == 1):
                m.d.sync += [
                        start.eq(self.input[0:36]),
                        time.eq(self.input[4:4+16])
                ]
            with m.Elif(self.input[36] == 1):
                m.d.sync += [
                        end.eq(self.input[0:36]),
                        diff[2:].eq(self.input[4:4+32] - start[4:4+32])
                        ]

        m.d.comb += [
                diff2.eq(diff + fine_end - fine_start),
                self.output.eq(Cat(diff2, time))
                ]

        m.submodules += s2v

        return m

if __name__ == "__main__":
    dut = TdcToHit()
    dut2 = SampleToVal()

    m = Module()
    m.submodules += [dut, dut2]

    sim = Simulator(m)

    def test_tdc2hit():
        yield dut.polarity.eq(RISING_IS_START)
        yield dut.input.eq((1 << 36) | (15 << 4) | 0b1110) # rising, sample = 1
        yield
        assert dut.output.eq(0)
        yield dut.input.eq((1 << 37) | (16 << 4) | 0b0011) # falling, sample = 1
        yield
        yield
        assert((yield dut.output) == (0b1111 << 16) | 5)

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
