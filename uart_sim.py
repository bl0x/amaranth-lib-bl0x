import os, pty

from amaranth import *
from amaranth.sim import *
from nmigen_lib import UART

class UartSim(Elaboratable):
    def __init__(self, base_freq, uart_freq):

        self.rx_data = Signal(unsigned(8))
        self.tx_data = Signal(unsigned(8))
        self.tx_trg = Signal()
        self.tx_rdy = Signal()

        self.base_freq = base_freq
        self.uart_freq = uart_freq

        self.master, self.slave = pty.openpty()
        name = os.ttyname(self.slave)
        print(f"Listening on {name}")

    def elaborate(self, platform):
        divisor = int(self.base_freq // self.uart_freq)
        uart = UART(divisor=divisor)

        m = Module()

        m.d.comb += [
                uart.tx_data.eq(self.tx_data),
                uart.tx_trg.eq(self.tx_trg),
                uart.rx_pin.eq(uart.tx_pin),
                self.tx_rdy.eq(uart.tx_rdy)
                ]

        m.submodules.uart = uart

        return m

    def read_char(self):
        c = os.read(self.master, 1)
        print(f"read_char: '{c}'")
        return c

if __name__ == '__main__':
    dut = UartSim(100e6, 115200)
    sim = Simulator(dut)

    def proc():
        while True:
            c = dut.read_char()
            yield dut.tx_data.eq(ord(c))
            yield dut.tx_trg.eq(1)
            yield
            yield dut.tx_trg.eq(0)
            yield
            if c == b'0':
                break
            while (yield dut.tx_rdy) == 0:
                yield

    sim.add_clock(1/10e6)
    sim.add_sync_process(proc)

    with sim.write_vcd('uart_sim.vcd', 'uart_sim_orig.gtkw'):
        sim.run_until(10)
