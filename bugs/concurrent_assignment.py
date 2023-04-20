from amaranth import *
from amaranth.sim import *

class ConcurrentAssignmentBug(Elaboratable):

    def __init__(self):
        self.inp = Signal(2)
        self.out = Signal(4)

    def Elaborate(self, platform):

        a = Signal(4)

        m = Module()

        m.d.sync += a[2:].eq(self.inp)

        m.d.comb += self.out.eq(a)

        return m
