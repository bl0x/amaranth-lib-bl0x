from amaranth import *
from amaranth.cli import main

# clock domain must be the same as for associated IDELAY

class IDELAYCTRL(Elaboratable):
    def __init__(self, refclk_domain):
        self.refclk_domain = refclk_domain

        self.ports = []

    def elaborate(self, platform):
        m = Module()
        m.submodules += Instance("IDELAYCTRL",
                i_REFCLK=ClockSignal(self.refclk_domain),
                i_RST=ResetSignal(self.refclk_domain)
                )
        return m

if __name__ == "__main__":
    idelayctrl = IDELAYCTRL("idelay")
    main(idelayctrl, ports=idelayctrl.ports)
