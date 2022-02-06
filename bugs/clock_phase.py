from amaranth import *
from amaranth.sim import *

phase0_fail = Signal()
phase90_fail = Signal()
phase180_fail = Signal()
phase270_fail = Signal()
phase0_correct = Signal()
phase90_correct = Signal()
phase180_correct = Signal()
phase270_correct = Signal()
check = Signal()

m = Module()
m.domains += ClockDomain("check")
m.domains += ClockDomain("phase0_fail")
m.domains += ClockDomain("phase90_fail")
m.domains += ClockDomain("phase180_fail")
m.domains += ClockDomain("phase270_fail")
m.domains += ClockDomain("phase0_correct")
m.domains += ClockDomain("phase90_correct")
m.domains += ClockDomain("phase180_correct")
m.domains += ClockDomain("phase270_correct")

m.d.comb += [
        check.eq(ClockSignal("check")),
        phase0_fail.eq(ClockSignal("phase0_fail")),
        phase90_fail.eq(ClockSignal("phase90_fail")),
        phase180_fail.eq(ClockSignal("phase180_fail")),
        phase270_fail.eq(ClockSignal("phase270_fail")),
        phase0_correct.eq(ClockSignal("phase0_correct")),
        phase90_correct.eq(ClockSignal("phase90_correct")),
        phase180_correct.eq(ClockSignal("phase180_correct")),
        phase270_correct.eq(ClockSignal("phase270_correct"))
        ]

sim = Simulator(m)
p = 1

sim.add_clock(p/8, phase=0, domain="check")

# This is what is desired (?)
sim.add_clock(p, phase=0*p/4, domain="phase0_fail")
sim.add_clock(p, phase=1*p/4, domain="phase90_fail")
sim.add_clock(p, phase=2*p/4, domain="phase180_fail")
sim.add_clock(p, phase=3*p/4, domain="phase270_fail")

# This is what is needed (!)
sim.add_clock(p, phase=1e12 * (p/2 + 0*p/8), domain="phase0_correct")
sim.add_clock(p, phase=1e12 * (p/2 + 1*p/8), domain="phase90_correct")
sim.add_clock(p, phase=1e12 * (p/2 + 2*p/8), domain="phase180_correct")
sim.add_clock(p, phase=1e12 * (p/2 + 3*p/8), domain="phase270_correct")

expected = [
        [0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0],
        ]

def proc():
    clocks = [
            phase0_fail,
            phase90_fail,
            phase180_fail,
            phase270_fail
            ]
    for i in range(16):
        yield
        for j, c in enumerate(clocks):
            #print(f"(i,j)=({i},{j}),
            #      clock = {yield c}, expect {expected[i][j]}")
            assert((yield c) == expected[j][i])

sim.add_sync_process(proc, domain="check")
with sim.write_vcd("bug_clock_phase.vcd"):
    sim.run_until(5)
