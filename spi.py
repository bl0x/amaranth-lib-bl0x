#!/usr/bin/env python3

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.sim import *
from edge_detect import EdgeDetector

class SpiDevice(wiring.Component):

    cs_n: In(1, init=1)
    sclk: In(1)
    sdi: In(1)
    sdo: Out(1)

    instr: Out(8)
    data: Out(24)
    busy: Out(1)
    ready: Out(1)
    w_en: In(1)
    w_data: In(32)

    def __init__(self):
        super().__init__()

    def elaborate(self, platform):
        cs_n = self.cs_n
        sdi = self.sdi
        sclk = self.sclk
        cnt_clk = Signal(6)
        n_bits = 32
        bits = Signal(n_bits)
        ed_sclk = EdgeDetector()

        m = Module()
        m.submodules.ed_sclk = ed_sclk

        m.d.comb += ed_sclk.input.eq(sclk)

        with m.FSM() as fsm:
            with m.State("IDLE"):
                with m.If(cs_n == 0):
                    m.d.sync += self.instr.eq(0)
                    m.d.sync += self.data.eq(0)
                    m.d.sync += cnt_clk.eq(0)
                    m.d.sync += self.busy.eq(0)
                    with m.If(self.w_en == 0):
                        m.next = "READ"
                    with m.Else():
                        m.next = "WRITE"
            with m.State("READ"):
                m.d.sync += self.ready.eq(0)
                with m.If(cs_n == 0):
                    m.d.comb += self.sdo.eq(bits[0])
                    with m.If(ed_sclk.rose == 1):
                        m.d.sync += bits.eq(Cat((bits[1:n_bits]), sdi))
                        m.d.sync += cnt_clk.eq(cnt_clk + 1)
                with m.Else():
                    m.d.sync += self.busy.eq(1)
                    m.next = "EXECUTE"
            with m.State("WRITE"):
                with m.If(cs_n == 0):
                    m.d.comb += self.sdo.eq(bits[0])
                    with m.If(self.w_en == 1):
                        m.d.sync += bits.eq(self.w_data)
                    with m.If(ed_sclk.rose == 1):
                        m.d.sync += bits.eq(Cat((bits[1:n_bits]), 0))
                        m.d.sync += cnt_clk.eq(cnt_clk + 1)
                with m.Else():
                    m.next = "IDLE"
            with m.State("EXECUTE"):
                m.d.sync += self.instr.eq(bits[0:8])
                m.d.sync += self.data.eq(bits[8:32])
                m.d.sync += self.ready.eq(1)
                m.next = "IDLE"


        return m

if __name__=="__main__":
    dut = SpiDevice()

    def write_byte(byte):
        for i in range(8):
            yield dut.sclk.eq(0)
            yield dut.sdi.eq(byte & 1)
            yield
            yield dut.sclk.eq(1)
            yield
            byte = byte >> 1

    def read_byte():
        for i in range(8):
            yield dut.sclk.eq(0)
            yield
            yield dut.sclk.eq(1)
            yield

    def start():
        yield dut.cs_n.eq(0)
        yield

    def stop():
        yield dut.cs_n.eq(1)
        yield

    def write_cycle():
        instr = 0x34
        data = [0x11, 0x22, 0x33]
        yield from write_byte(instr)
        for i in range(3):
            yield from write_byte(data[i])
        yield

    def read_cycle():
        yield dut.w_en.eq(1)
        yield
        yield dut.w_data.eq(0x12345678)
        yield
        yield dut.w_en.eq(0)
        yield
        for i in range(4):
            yield from read_byte()
        yield

    def init():
        yield dut.cs_n.eq(1)
        yield dut.sdi.eq(0)
        yield dut.sclk.eq(0)
        yield

    def proc():
        yield from init()
        yield
        for i in range(20):
            yield
        yield from start()
        yield from write_cycle()
        yield from write_cycle()
        yield from stop()
        yield from start()
        yield from read_cycle()
        yield from stop()
        yield

    sim = Simulator(dut)
    sim.add_clock(1/10e6)
    sim.add_sync_process(proc)
    with sim.write_vcd('tb_spi.vcd', 'tb_spi_orig.gtkw'):
        sim.run()
