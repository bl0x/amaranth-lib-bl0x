from nmigen import *
from nmigen.sim import *

class SerialEncoder(Elaboratable):
    def __init__(self, bufsize=16):
        self.bufsize = bufsize
        self.buffer = Array([Signal(unsigned(8)) for _ in range(self.bufsize)])
        self.len = Signal(unsigned(8))
        self.trg = Signal()
        self.rdy = Signal()
        self.tx = Signal(unsigned(8))
        self.tx_rdy = Signal()
        self.tx_trg = Signal()

    def elaborate(self, platform):
        m = Module()

        return m
