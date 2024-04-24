from amaranth import Module, Signal, Elaboratable, Const
from amaranth.hdl.mem import Memory
from amaranth_boards.cmod_s7 import CmodS7_Platform
from amaranth.back import verilog

# This tests whether or not memory is instantiated as block RAM or
# distributed RAM.

# Test with these commits of amaranth-hdl:
# 8c4a15a -> infers distributed RAM
# fc85feb -> infers block RAM

class MemoryBramRegression(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        # led as output
        led = platform.request('led', 0)

        # counter to produce data
        counter = Signal(32)

        # memory to be instantiated as BRAM
        mem = Memory(width=32, depth=8000)
        w = m.submodules.write = mem.write_port()
        r = m.submodules.read = mem.read_port()

        # Increase counter on every clock cycle
        m.d.sync += counter.eq(counter + 1)

        # Connect mem to counter and led
        # Address increments on every clock cycle,
        # Write data is the full counter value
        # Enable is only active on every other clock cycle
        # Read address is running slower by a factor 4
        # Led should blink (but that is irrelevant for the test case)

        m.d.comb += [
            w.addr.eq(counter[0:13]),
            w.data.eq(counter),
            w.en.eq(Const(1)),
            r.addr.eq(counter[2:15]),
            led.o.eq(r.data[0])
        ]
        return m

if __name__ == "__main__":
    top = MemoryBramRegression()
    platform = CmodS7_Platform(toolchain="Vivado")
    platform.build(top)
