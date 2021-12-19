from amaranth import *
from amaranth.cli import main

class ISERDESE2(Elaboratable):
    def __init__(self, mode):

        # input signal (without IDELAY)
        self.d = Signal()

        # input signal (form IDELAY)
        self.ddly = Signal()

        # driving clocks
        self.clk = Signal()
        self.clkb = Signal()
        self.oclk = Signal()
        self.oclkb = Signal()

        self.rst = Signal()

        # output samples (in order)
        self.s = Signal(4)

        # unused outputs
        self.q = Signal(8)
        self.o = Signal()
        self.shiftout = Signal(2)

        self.mode = mode
        valid_modes = ["OVERSAMPLE"]
        assert(self.mode in valid_modes)

        self.params = {}
        if self.mode == "OVERSAMPLE":
            self.do_oversample()

        self.ports = [
                self.d,
                self.ddly,
                self.clk,
                self.clkb,
                self.oclk,
                self.oclkb,
                self.s
                ]

    def do_oversample(self):
        self.params.update(
                p_DATA_RATE="DDR",
                p_DATA_WIDTH=4,
                p_DYN_CLKDIV_INV_EN="FALSE",
                p_DYN_CLK_INV_EN="FALSE",
                p_INIT_Q1=0,
                p_INIT_Q2=0,
                p_INIT_Q3=0,
                p_INIT_Q4=0,
                p_INTERFACE_TYPE="OVERSAMPLE", # oversample supported?
                p_IOBDELAY="NONE",
                #p_IOBDELAY="IFD",
                p_NUM_CE="2",
                #p_OFB_USED="FALSE",
                p_SERDES_MODE="MASTER",
                p_SRVAL_Q1=0,
                p_SRVAL_Q2=0,
                p_SRVAL_Q3=0,
                p_SRVAL_Q4=0,
                i_BITSLIP=0,
                i_CE1=1,
                i_CE2=1,
                i_CLK=self.clk,
                i_CLKB=self.clkb,
                i_CLKDIV=0,
                #i_CLKDIVP=0,
                i_D=self.d,
                i_DDLY=self.ddly,
                #i_DYNCLKDIVPSEL=0, # why is this in arch.timing.xml?
                #i_DYNCLKDIVSEL=0,
                #i_DYNCLKSEL=0,
                #i_OCLK=self.oclk,
                #i_OCLKB=self.oclkb,
                #i_OFB=0,
                i_RST=self.rst,
                #i_SHIFTIN1=0,
                #i_SHIFTIN2=0,
                #i_TFB=0, # why is this in arch def? arch.timing.xml
                #o_O=self.o,
                o_Q1=self.s[0],
                o_Q2=self.s[2],
                o_Q3=self.s[1],
                o_Q4=self.s[3],
                o_Q5=self.q[4],
                o_Q6=self.q[5],
                o_Q7=self.q[6],
                o_Q8=self.q[7],
                #o_SHIFTOUT1=self.shiftout[0],
                #o_SHIFTOUT2=self.shiftout[1]
                )

    def elaborate(self, platform):
        m = Module()
        m.submodules += Instance("ISERDESE2", **self.params)
        return m

if __name__ == '__main__':
    iserdes = ISERDESE2("OVERSAMPLE")
    main(iserdes, ports=iserdes.ports)
