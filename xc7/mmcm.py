from amaranth import *
from amaranth.cli import main

# supports a subset of the Xilinx Series 7 MMCME2_ADV features
# inspired by / taken from:
# https://github.com/kbob/nmigen-examples/blob/master/nmigen_lib/pll.py
# and
# https://github.com/enjoy-digital/litex/blob/master/litex/soc/cores/clock/xilinx_s7.py
# check also this: https://41j.com/blog/2020/01/ice40hx8k-ad9225-adc-with-amaranth/

class MMCME2(Elaboratable):
    clkout0_divide_range = (1, (128 + 1/8), 1/8)
    clkout_divide_range = (1, 128+1)
    clkfbout_mult_range = (2, 64+1)
    divclk_divide_range = (1, 106+1)
    clkin_range = (10e6, 800e6)
    vco_range = (600e6, 1200e6)

    def __init__(self, freq_in, domain="sync"):
        self.freq_in = freq_in
        self._domain = domain

        self.clkin = ClockSignal(self._domain)
        self.reset = Signal()
        self.locked = Signal()

        self.config = {}

        self.outputs = []

        self.ports = [
                self.clkin,
                self.reset,
                self.locked
                ]

        self.m = Module()

    def create_clkout(self, domain_name, frequency, phase=0):
        clkbuf_in = Signal(name=f"clkbuf_in_{len(self.outputs)}")
        clkbuf_out = Signal(name=f"clkbuf_out_{len(self.outputs)}")

        self.outputs.append((clkbuf_in, clkbuf_out, frequency, phase))

        self.m.submodules += Instance("BUFG",
                i_I=clkbuf_in,
                o_O=clkbuf_out
                )

        # self.m.domains += ClockDomain(domain_name)
        self.m.d.comb += ClockSignal(domain_name).eq(clkbuf_out)

        print(f"New clock domain '{domain_name}' with frequency {frequency}")

    def make_config(self):
        config = {}

        # fixed for now
        divclk_divide = 1
        config["divclk_divide"] = divclk_divide

        m = 0
        d = 0

        for m in range(*self.clkfbout_mult_range):
            all_valid = True
            vco_freq = self.freq_in * m / divclk_divide
            if vco_freq > self.vco_range[1] or vco_freq < self.vco_range[0]:
                continue
            for n, (_, _, freq, phase) in enumerate(self.outputs):
                valid = False
                for d in range(*self.clkout_divide_range):
                    f = vco_freq / d
                    if f == freq:
                        config[f"clkout{n}_freq"] = freq
                        config[f"clkout{n}_divide"] = d
                        config[f"clkout{n}_phase"] = phase
                        valid = True
                        break
                if not valid:
                    all_valid = False
            if all_valid:
                break

        assert(all_valid), f"No valid parameters for frequency {freq}"

        config["clkfbout_mult"] = m
        print(f"m = {m} d = {d}")
        print(config)

        return config

    def elaborate(self, platform):
        mmcm_fb = Signal()

        self.config = self.make_config()

        params = {}

        params.update(
            i_CLKFBIN=mmcm_fb,
            i_CLKIN1=self.clkin,
            i_RST=self.reset,
            o_CLKFBOUT=mmcm_fb,
            o_LOCKED=self.locked,
            p_BANDWIDTH="OPTIMIZED",
            p_CLKFBOUT_MULT_F=self.config["clkfbout_mult"],
            p_CLKIN1_PERIOD=1e9/self.freq_in,
            p_COMPENSATION="ZHOLD",
            p_DIVCLK_DIVIDE=self.config["divclk_divide"],
            p_REF_JITTER1=0.01
            )

        for n, (clk_in, clk_out, freq, phase) in enumerate(self.outputs):
            div = f"p_CLKOUT{n}_DIVIDE"
            if n == 0:
                div = div + "_F"

            params[f"o_CLKOUT{n}"] = clk_in
            params[div] = self.config[f"clkout{n}_divide"]
            params[f"p_CLKOUT{n}_PHASE"] = self.config[f"clkout{n}_phase"]
            params[f"p_CLKOUT{n}_DUTY_CYCLE"] = 0.5

        print(f"ports = {self.ports}")

        self.m.submodules += Instance("MMCME2_ADV", **params)

        return self.m

if __name__ == '__main__':
    mmcme2 = MMCME2(12e6)
    mmcme2.create_clkout("test192", 192e6, 0)
    mmcme2.create_clkout("test192_90", 192e6, 90)
    main(mmcme2, ports=mmcme2.ports)
