from amaranth import *
from amaranth.sim import *
from amaranth.lib.fifo import AsyncFIFO
from amaranth.lib.cdc import PulseSynchronizer

from histogram import Histogram
from tdc_channel import TdcChannel
from edge_detect import EdgeDetector

class TdcHistogram(Elaboratable):
    def __init__(self, name, fast_domain="fast", fast_90_domain="fast_90",
            tdc_domain="tdc", bins=10, bits=8):
        self.name = name
        self.bins = bins
        self.bits = bits
        self.fast_domain = fast_domain
        self.fast_90_domain = fast_90_domain
        self.tdc_domain = tdc_domain

        # TDC
        self.time = Signal(32)
        self.input = Signal()

        # Rebinning
        self.shift = Signal(range(0, 15))

        self.counter = Signal(16)

        # Histogram
        self.index_r = Signal(range(1, self.bins))
        self.index_w = Signal(range(1, self.bins))
        self.read = Signal()
        self.write = Signal()
        self.increment = Signal()
        self.data_r = Signal(16)
        self.data_w = Signal(16)

        # Debug outputs
        self.debug_tdc_rdy = Signal()
        self.debug_fifo_rdy = Signal()
        self.debug_hit_rdy = Signal()

        # Control signals
        self.go = Signal()
        self.clear = Signal()

    def connect(self, signal=None, time=None, counter=None, shift=None,
            go=None, clear=None):
        return [
            self.time.eq(time),
            self.input.eq(signal),
            counter.eq(self.counter),
            self.shift.eq(shift),
            self.go.eq(go),
            self.clear.eq(clear)
        ]

    def elaborate(self, platform):

        histogram = Histogram(bins=self.bins, bits=self.bits)
        tdc = DomainRenamer(self.tdc_domain)(TdcChannel(self.name))
        fifo = AsyncFIFO(width=32, depth=8, w_domain=self.tdc_domain,
                r_domain="sync")

        we_tdc = Signal()
        incr_tdc = Signal()
        incr_tdc_sync = Signal()
        incr_up = Signal()
        incr_down = Signal()
        incr_start = Signal()
        busy = Signal()
        addr_tdc = Signal(16)
        addr_clear = Signal(16)

        strobe = Signal()
        strobe_tdc = Signal()
        strobe_start = Signal()

        tdc_data = Signal(32)
        tdc_time = Signal(16) # Unused as of now
        tdc_value = Signal(16)

        increment_sync   = PulseSynchronizer(self.tdc_domain, "sync")
        incr_up_det      = DomainRenamer(self.tdc_domain)(EdgeDetector())
        incr_down_det    = DomainRenamer(self.tdc_domain)(EdgeDetector())
        strobe_sync      = PulseSynchronizer("sync", self.tdc_domain)
        strobe_start_det = EdgeDetector()

        m = Module()

        m.submodules.increment_sync = increment_sync
        m.submodules.histogram = histogram
        m.submodules.tdc = tdc
        m.submodules.fifo = fifo
        m.submodules.incr_up_det      = incr_up_det
        m.submodules.incr_down_det    = incr_down_det
        m.submodules.strobe_sync      = strobe_sync
        m.submodules.strobe_start_det = strobe_start_det

        m.d.comb += [
            fifo.w_data.eq(tdc.output),
            fifo.w_en.eq(tdc.hit_rdy_pulse),
            fifo.r_en.eq(fifo.r_rdy),
            tdc_data.eq(Mux((fifo.r_level > 0), fifo.r_data, 0)),
            tdc_value.eq(tdc_data[0:15] >> self.shift),
            tdc_time.eq(tdc_data[16:31])
        ]

        with m.If(incr_up == 1):
            m.d[self.tdc_domain] += busy.eq(1)
        with m.If(incr_down == 1):
            m.d[self.tdc_domain] += busy.eq(0)

        m.d.comb += [
            tdc.strobe.eq(strobe_tdc),
            tdc.input.eq(self.input),
            tdc.time.eq(self.time),
            tdc.enable.eq(1),
            self.debug_tdc_rdy.eq(tdc.tdc_rdy),
            self.debug_fifo_rdy.eq(tdc.fifo_rdy),
            self.debug_hit_rdy.eq(tdc.hit_rdy)
        ]

        # Counter
        m.d.comb += [
            self.counter.eq(tdc.counter)
        ]

        # Synchronise read strobe pulse to TDC domain
        m.d.comb += [
            strobe_sync.i.eq(strobe_start),
            strobe_tdc.eq(strobe_sync.o)
        ]

        m.d.comb += [
            strobe_start_det.input.eq(strobe),
            strobe_start.eq(strobe_start_det.rose)
        ]

        with m.If((busy == 0) & (tdc.fifo_rdy)):
            m.d.sync += strobe.eq(1)
        with m.Else():
            m.d.sync += strobe.eq(0)

        addr_tdc_max = self.bins - 1
        print(f"Maximum tdc histogram address = {addr_tdc_max}")

        with m.If(self.clear == 0):
            m.d.comb += addr_tdc.eq(Mux(tdc_value > addr_tdc_max,
                addr_tdc_max, tdc_value))
        with m.Else():
            m.d.comb += addr_tdc.eq(addr_clear)

        with m.If(self.clear == 1):
            with m.If(addr_clear == addr_tdc_max):
                m.d.sync += addr_clear.eq(0)
            with m.Else():
                m.d.sync += addr_clear.eq(addr_clear + 1)

        # Write to histogram and remove from fifo
        m.d.comb += [
            incr_tdc.eq(fifo.r_rdy)
        ]

        # Writing to histogram
        with m.If((incr_tdc | we_tdc) & (self.go == 1)):
            m.d.comb += [
                self.index_w.eq(addr_tdc),
                self.write.eq(we_tdc),
                self.increment.eq(incr_tdc)
            ]
        with m.Elif((self.go == 0) & (self.clear == 1)):
            m.d.comb += [
                self.index_w.eq(addr_tdc),
                self.write.eq(1),
                self.data_w.eq(0)
            ]


        # connect to histogram
        m.d.comb += [
            histogram.index_r.eq(self.index_r),
            histogram.index_w.eq(self.index_w),
            histogram.data_w.eq(self.data_w),
            self.data_r.eq(histogram.data_r),
            histogram.increment.eq(self.increment),
            histogram.write.eq(self.write),
            histogram.read.eq(self.read)
        ]

        return m
