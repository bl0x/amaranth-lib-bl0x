from amaranth.back import verilog
from xc7.mmcm import MMCME2

top = MMCME2(12e6, 100e6)
with open("mmcme2.v", "w") as f:
    f.write(verilog.convert(top, ports=top.ports))
