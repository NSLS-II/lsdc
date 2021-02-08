#objects available should be zebra, vector, eiger
import bluesky.plan_stubs as bps

def zebraDaqPrep():
       RESET_GROUP = 'reset'
       yield from bps.abs_set(zebra.reset, 1, group=RESET_GROUP)
       yield from bps.wait(RESET_GROUP)
       yield from bps.sleep(2.0)
       yield from bps.mv(zebra.out1, 31)
       yield from bps.mv(zebra.m1_set_pos, 1)
       yield from bps.mv(zebra.m2_set_pos, 1)
       yield from bps.mv(zebra.m3_set_pos, 1)
       yield from bps.mv(zebra.pc.arm_sel, 1)
