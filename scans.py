#objects available should be zebra, vector, eiger
from bluesky.plan_stubs import mv
import time

def zebraDaqPrep():
       yield from mv(zebra.reset, 1)
       time.sleep(2.0)
       #yield from mv(zebra.ttlSel, 31)
       yield from mv(zebra.m1_set_pos, 1)
       yield from mv(zebra.m2_set_pos, 1)
       yield from mv(zebra.m3_set_pos, 1)
       #yield from mv(zebra.armTrigSource, 1)
