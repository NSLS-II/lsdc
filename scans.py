#objects available should be zebra, vector, eiger
import bluesky.plan_stubs as bps
from start_bs import zebra

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

def setupZebraVectorScan(angle_start, gate_width, scan_width, pulse_width, pulse_step, exposure_period_per_image, num_images, is_still=False):
    yield from bps.mv(zebra.pc.gate.sel, angle_start)
    if is_still is False:
        yield from bps.mv(zebra.pc.gate.width, gate_width)
        yield from bps.mv(zebra.pc.gate.step, scan_width)
    yield from bps.mv(zebra.pc.gate.num_gates, 1)
    yield from bps.mv(zebra.pc.pulse.start, 0)
    yield from bps.mv(zebra.pc.pulse.width, pulse_width)
    yield from bps.mv(zebra.pc.pulse.step, pulse_step)
    yield from bps.mv(zebra.pc.pulse.delay, exposure_period_per_image/2*1000)
    yield from bps.mv(zebra.pc.pulse.max, num_images)

def setupZebraVectorScanForRaster(angle_start, image_width, exposure_time_per_image, exposure_period_per_image, detector_dead_time, num_images, scan_encoder=3):
    VECTOR_SCAN_GROUP = 'vector_scan'
    yield from bps.abs_set(zebra.pc.encoder, scan_encoder, group=VECTOR_SCAN_GROUP)
    yield from bps.wait(VECTOR_SCAN_GROUP)
    yield from bps.sleep(1.0)
    yield from bps.mv(zebra.pc.direction, 0) # 0 = positive
    yield from bps.mv(zebra.pc.gate.sel, 0)
    yield from bps.mv(zebra.pc.gate.start, angle_start)
    if image_width != 0:
        yield from bps.mv(zebra.pc.gate.width, num_images * image_width)
        yield from bps.mv(zebra.pc.gate.step, num_images * image_width + 0.001)
    yield from bps.mv(zebra.pc.gate.num_gates, 1)
    yield from bps.mv(zebra.pc.pulse.sel, 1)
    yield from bps.mv(zebra.pc.pulse.start, 0)
    yield from bps.mv(zebra.pc.pulse.width, (exposure_time_per_image - detector_dead_time) * 1000)
    yield from bps.mv(zebra.pc.pulse.step, exposure_period_per_image * 1000)
    yield from bps.mv(zebra.pc.pulse.delay, exposure_period_per_image / 2 * 1000)
