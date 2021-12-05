from nmigen import *
from nmigen.cli import main

import math

# This is a fixed IDELAY
# Requires in addition an associated IDELAYCTRL module

class IDELAYE2(Elaboratable):
    def __init__(self, delay_s, reference_frequency_hz):
        self.idatain = Signal()
        self.dataout = Signal()

        self.ports = [
                self.idatain,
                self.dataout
                ]

        self.delay_s = delay_s
        self.reference_frequency_hz = reference_frequency_hz

        self.valid_ref_ranges = [
                range(int(190e6),int(211e6)),
                range(int(290e6),int(311e6))
                ]
        assert(any(
            [reference_frequency_hz in r for r in self.valid_ref_ranges]))

        self.resolution = 1/(self.reference_frequency_hz * 2 * 32)

        self.tap = math.ceil(self.delay_s / self.resolution)
        assert(self.tap in range(0, 32))
        
    def elaborate(self, platform):
        params = {}

        params.update(
                p_CINVCTRL_SEL="FALSE",
                p_DELAY_SRC="IDATAIN",
                p_HIGH_PERFORMANCE_MODE="TRUE",
                p_IDELAY_TYPE="FIXED",
                p_IDELAY_VALUE=self.tap,
                p_PIPE_SEL="FALSE",
                p_REFCLK_FREQUENCY=self.reference_frequency_hz/1e6,
                p_SIGNAL_PATTERN="DATA",
                i_C = ClockSignal(),
                i_CE = 0,
                i_CINVCTRL = 0,
                i_CNTVALUEIN = 0,
                i_DATAIN = 0,
                i_IDATAIN = self.idatain,
                i_INC = 0,
                i_LD = 0,
                i_LDPIPEEN = 0,
                #o_CNTVALUEOUT = 0,
                o_DATAOUT = self.dataout
                )

        m = Module()
        m.submodules += Instance("IDELAYE2", **params)
        return m

if __name__ == "__main__":
    idelay = IDELAYE2(200e-12, 200e6)
    main(idelay, ports=idelay.ports)
