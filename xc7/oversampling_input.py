from nmigen import *
from nmigen.cli import main

#from xc7.idelay import IDELAYE2
#from xc7.idelayctrl import IDELAYCTRL
from xc7.iserdes import ISERDESE2
from xc7.mmcm import MMCME2

class OversamplingInput(Elaboratable):
    def __init__(self):
        self.input_pin = Signal()
        self.data4 = Signal(4)

        self.ports = [
                self.input_pin,
                self.data4
                ]

    def elaborate(self, platform):
        base_freq = 12e6
        iserdes_freq = base_freq * 32 # 384 : ~2.5 ns -> 625 ps resolution
        #idelay_freq = base_freq * 16  # 192

        mmcm = MMCME2(base_freq)
        mmcm.create_clkout("iserdes_0", frequency=iserdes_freq, phase=0)
        mmcm.create_clkout("iserdes_90", frequency=iserdes_freq, phase=90)
        #mmcm.create_clkout("idelay_ref", frequency=idelay_freq)

        #idelay = IDELAYE2(0, idelay_freq)
        #idelayctrl = IDELAYCTRL("idelay_ref")
        iserdes = ISERDESE2("OVERSAMPLE")

        m = Module()
        m.d.comb += [
                #idelay.idatain.eq(self.input_pin),
                #iserdes.ddly.eq(idelay.dataout),
                iserdes.d.eq(self.input_pin),
                iserdes.clk.eq(ClockSignal("iserdes_0")),
                iserdes.clkb.eq(~ClockSignal("iserdes_0")),
                iserdes.oclk.eq(ClockSignal("iserdes_90")),
                iserdes.oclkb.eq(~ClockSignal("iserdes_90")),
                iserdes.rst.eq(ResetSignal("iserdes_0")),
                self.data4.eq(iserdes.s)
                ]

        m.submodules += [
                mmcm,
                #idelayctrl,
                #idelay,
                iserdes
                ]
        return m

if __name__ == "__main__":
    oversample = OversamplingInput()
    main(oversample, ports=oversample.ports)
