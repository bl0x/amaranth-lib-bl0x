from nmigen import *
from nmigen.cli import main

# supports a subset of the Xilinx Series 7 MMCME2_ADV features
# inspired by / taken from:
# https://github.com/enjoy-digital/litex/blob/master/litex/soc/cores/clock/xilinx_s7.py

class MMCME2(Elaboratable):

    def __init__(self, freq_in, freq_out, domain_name='sync'):
        self.freq_in = freq_in
        self.freq_out = freq_out
        self.domain_name = domain_name
        self.domain = ClockDomain(domain_name)

        self.clkin = Signal()
        self.reset = Signal()

        self.locked = Signal()
        self.clkout0 = Signal()
        self.clkout0_buf = ClockSignal(self.domain_name)

        self.clkout0_divide_range = (1, (128 + 1/8), 1/8)
        self.clkout_divide_range = (1, 128+1)
        self.clkfbout_mult_range = (2, 64+1)
        self.divclk_divide_range = (1, 106+1)
        self.clkin_range = (10e6, 800e6)
        self.vco_range = (600e6, 1200e6)

        self.config = self.make_config()

        self.ports = [
                self.clkin,
                self.domain.clk,
                self.domain.rst
                ]

    def make_config(self):
        config = {}
        config["clkfbout_mult"] = 1
        config["divclk_divide"] = 1
        config["clkout0_freq"] = 1
        config["clkout0_divide"] = 1
        config["clkout0_phase"] = 1
        return config

    def elaborate(self, platform):
        mmcm_fb = Signal()

        obuf = Instance("BUFG",
                i_I=self.clkout0,
                o_O=self.clkout0_buf
                )

        mmcme2 = Instance("MMCME2_ADV",
                i_CLKFBIN=mmcm_fb,
                i_CLKIN1=self.clkin,
                i_RST=self.reset,
                o_CLKFBOUT=mmcm_fb,
                o_LOCKED=self.locked,
                o_CLKOUT0=self.clkout0,
                p_BANDWIDTH="OPTIMIZED",
                p_CLKFBOUT_MULT_F=self.config["clkfbout_mult"],
                p_CLKIN1_PERIOD=1e9/self.freq_in,
                p_DIVCLK_DIVIDE=self.config["divclk_divide"],
                p_REF_JITTER1=0.01,
                p_CLKOUT0_DIVIDE_F=self.config["clkout0_divide"],
                p_CLKOUT0_PHASE=self.config["clkout0_phase"]
                )


        m = Module()
        m.submodules += [obuf, mmcme2]
        return m

if __name__ == '__main__':
    mmcme2 = MMCME2(12e6, 100e6)
    main(mmcme2, ports=mmcme2.ports)
