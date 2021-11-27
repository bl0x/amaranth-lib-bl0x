from nmigen import *
from nmigen.cli import main

class ISERDESE2(Elaboratable):
    def __init__(self, mode):
        self.ddly = Signal()
        self.clk = Signal()
        self.clkb = Signal()
        self.oclk = Signal()
        self.oclkb = Signal()
        self.q1 = Signal()
        self.q2 = Signal()
        self.q3 = Signal()
        self.q4 = Signal()

        self.mode = mode
        valid_modes = ["OVERSAMPLE"]
        assert(self.mode in valid_modes)

        self.params = {}
        if self.mode == "OVERSAMPLE":
            self.do_oversample()

        self.ports = [
                self.ddly,
                self.clk,
                self.clkb,
                self.oclk,
                self.oclkb,
                self.q1,
                self.q2,
                self.q3,
                self.q4
                ]

    def do_oversample(self):
        self.params.update(
                p_INTERFACE_TYPE="OVERSAMPLE",
                p_SERDES_MODE="MASTER",
                p_DATA_WIDTH=4,
                p_DATA_RATE="DDR",
                p_OFB_USED="FALSE",
                p_IOBDELAY="IFD",
                p_NUM_CE="1",
                p_DYN_CLKDIV_INV_EN="FALSE",
                p_DYN_CLK_INV_EN="FALSE",
                p_INST_Q1=0,
                p_INST_Q2=0,
                p_INST_Q3=0,
                p_INST_Q4=0,
                p_SRVAL_Q1=0,
                p_SRVAL_Q2=0,
                p_SRVAL_Q3=0,
                p_SRVAL_Q4=0
                )

    def elaborate(self, platform):
        m = Module()
        m.submodules += Instance("SERDESE2", **self.params)
        return m

if __name__ == '__main__':
    iserdes = ISERDESE2("OVERSAMPLE")
    main(iserdes, ports=iserdes.ports)
