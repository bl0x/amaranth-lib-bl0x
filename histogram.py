#!/usr/bin/env nmigen

from nmigen import *
from nmigen.sim import *

class Histogram(Elaboratable):

    def __init__(self, bins=100, bits=8):
        self.bins = bins
        self.bits = bits
        self.mem = Array([Signal(unsigned(self.bits)) for _ in range(bins)])
        self.index_r = Signal(range(1, self.bins))
        self.index_w = Signal(range(1, self.bins))
        self.data = Signal(unsigned(self.bits))
        self.increment = Signal()
        self.write = Signal()
        self.read = Signal()

        self.ports = (
                self.index_r,
                self.index_w,
                self.data,
                self.increment,
                self.write,
                self.read
                )

    def elaborate(self, platform):
        m = Module()

        # Writing
        with m.If(self.increment == 1):
            m.d.sync += self.mem[self.index_w].eq(self.mem[self.index_w] + 1)
        with m.Elif(self.write == 1):
            m.d.sync += self.mem[self.index_w].eq(self.data)

        # Reading
        with m.If(self.read == 1):
            m.d.sync += self.data.eq(self.mem[self.index_r])

        return m

if __name__ == '__main__':
    dut = Histogram(bins=8, bits=8)

    sim = Simulator(dut)

    def write(value, index):
        # set a bin at index to a value
        yield dut.index_w.eq(index)
        yield dut.data.eq(value)
        yield dut.write.eq(1)
        yield Tick()
        yield Settle()

        # reset write
        yield dut.write.eq(0)
        yield dut.data.eq(0)
        yield Tick()
        yield Settle()

    def read(index):
        # read
        yield dut.index_r.eq(index)
        yield dut.read.eq(1)
        yield Tick()
        yield Settle()

        # reset read
        yield dut.read.eq(0)
        yield Tick()
        yield Settle()

    def increment(index):
        # increment
        yield dut.index_w.eq(index)
        yield dut.increment.eq(1)
        yield Tick()
        yield Settle()

        # reset increment
        yield dut.increment.eq(0)
        yield Tick()
        yield Settle()

    def proc():
        yield from write(24, 4)
        yield from read(4)

        print("dut.data = {}".format((yield dut.data)))
        assert (yield dut.data) == 24, "Didn't get 24!"

        yield from increment(4)
        yield from read(4)

        print("dut.data = {}".format((yield dut.data)))
        assert (yield dut.data) == 25, "Didn't get 25!"

        yield from increment(1)
        yield from read(1)

        print("dut.data = {}".format((yield dut.data)))
        assert (yield dut.data) == 1, "Didn't get 1!"


    sim.add_clock(1e-6)
    sim.add_sync_process(proc)
    with sim.write_vcd('histogram.vcd', 'histogram.gtkw', traces=dut.ports):
        sim.run()
