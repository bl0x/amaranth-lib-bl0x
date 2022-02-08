from amaranth import *
from amaranth.sim import *

class Histogram(Elaboratable):

    def __init__(self, bins=100, bits=8):
        self.bins = bins
        self.bits = bits
        self.mem = Array([Signal(unsigned(self.bits)) for _ in range(bins)])
        self.index_r = Signal(range(1, self.bins))
        self.index_w = Signal(range(1, self.bins))
        self.data_r = Signal(unsigned(self.bits))
        self.data_w = Signal(unsigned(self.bits))
        self.increment = Signal()
        self.write = Signal()
        self.read = Signal()

        self.ports = (
            self.index_r,
            self.index_w,
            self.data_r,
            self.data_w,
            self.increment,
            self.write,
            self.read
        )

    def elaborate(self, platform):
        m = Module()

        w_en = Signal()
        w_data = Signal(self.bits)
        r_addr = Signal(range(1, self.bins))
        increment_delayed = Signal()

        storage = Memory(width=self.bits, depth=self.bins)
        w_port = m.submodules.w_port = storage.write_port()
        r_port = m.submodules.r_port = storage.read_port()

        m.d.comb += [
            w_port.addr.eq(self.index_w),
            w_port.data.eq(w_data),
            w_port.en.eq(w_en),
            r_port.addr.eq(r_addr),
            self.data_r.eq(r_port.data),
        ]

        m.d.sync += increment_delayed.eq(self.increment)

        m.d.comb += w_en.eq(self.write | increment_delayed)
        m.d.comb += r_addr.eq(Mux(self.increment, self.index_w, self.index_r))
        m.d.comb += w_data.eq(Mux(increment_delayed, r_port.data + 1, self.data_w))

        # Old handling without memory
        ## Writing
        #with m.If(self.increment == 1):
        #    m.d.sync += self.mem[self.index_w].eq(self.mem[self.index_w] + 1)
        #with m.Elif(self.write == 1):
        #    m.d.sync += self.mem[self.index_w].eq(self.data_w)

        ## Reading
        #with m.If(self.read == 1):
        #    m.d.sync += self.data_r.eq(self.mem[self.index_r])

        return m

if __name__ == '__main__':
    dut = Histogram(bins=8, bits=8)

    sim = Simulator(dut)

    def write(value, index):
        # set a bin at index to a value
        yield dut.index_w.eq(index)
        yield dut.data_w.eq(value)
        yield dut.write.eq(1)
        yield

        # reset write
        yield dut.write.eq(0)
        yield dut.data_w.eq(0)
        yield

    def read(index):
        # read
        yield dut.index_r.eq(index)
        yield dut.read.eq(1)
        yield

        # reset read
        yield dut.read.eq(0)
        yield

    def increment(index):
        # increment
        yield dut.index_w.eq(index)
        yield dut.increment.eq(1)
        yield

        # reset increment
        yield dut.increment.eq(0)
        yield

    def proc():
        yield from write(24, 4)
        yield from read(4)

        print("dut.data_r = {}".format((yield dut.data_r)))
        assert (yield dut.data_r) == 24, "Didn't get 24!"

        yield from read(0)

        print("dut.data_r = {}".format((yield dut.data_r)))
        assert (yield dut.data_r) == 0, "Didn't get 0!"

        yield from increment(4)
        yield from read(4)

        print("dut.data = {}".format((yield dut.data_r)))
        assert (yield dut.data_r) == 25, "Didn't get 25!"

        yield from increment(1)
        yield from read(1)

        print("dut.data = {}".format((yield dut.data_r)))
        assert (yield dut.data_r) == 1, "Didn't get 1!"


    sim.add_clock(1e-6)
    sim.add_sync_process(proc)
    with sim.write_vcd('histogram.vcd', 'histogram.gtkw', traces=dut.ports):
        sim.run()
