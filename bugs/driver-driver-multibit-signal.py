from nmigen import *
from nmigen.cli import main

class MultibitDriverConflict(Elaboratable):
    def elaborate(self, platform):
        #a = Signal(2)
        a = [Signal() for i in range(2)]
        m = Module()
        m.domains += [ ClockDomain("c1"), ClockDomain("c2") ]
        m.d.c1 += a[0].eq(1)
        m.d.c2 += a[1].eq(1)
        return m

if __name__ == "__main__":
    test = MultibitDriverConflict()
    main(test)
