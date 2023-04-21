#objects available should be zebra, vector, eiger
import bluesky.plan_stubs as bps

def zebra_daq_prep(zebra):
       yield from bps.mv(zebra.reset, 1)
       yield from bps.sleep(2.0)
       yield from bps.mv(zebra.out1, 31,
                         zebra.m1_set_pos, 1,
                         zebra.m2_set_pos, 1,
                         zebra.m3_set_pos, 1,
                         zebra.pc.gate.sel, 1)

def setup_zebra_vector_scan(zebra, angle_start, gate_width, scan_width, pulse_width, pulse_step, exposure_period_per_image, num_images, is_still=False):
    yield from bps.mv(zebra.pc.gate.sel, angle_start)
    if is_still is False:
        yield from bps.mv(zebra.pc.gate.width, gate_width,
                          zebra.pc.gate.step, scan_width)
    yield from bps.mv(zebra.pc.gate.num_gates, 1,
                      zebra.pc.pulse.start, 0,
                      zebra.pc.pulse.width, pulse_width,
                      zebra.pc.pulse.step, pulse_step,
                      zebra.pc.pulse.delay, exposure_period_per_image / 2 * 1000,
                      zebra.pc.pulse.max, num_images)

def setup_zebra_vector_scan_for_raster(zebra, angle_start, image_width, exposure_time_per_image, exposure_period_per_image, detector_dead_time, num_images, scan_encoder=3):
    yield from bps.mv(zebra.pc.encoder, scan_encoder)
    yield from bps.sleep(1.0)
    yield from bps.mv(zebra.pc.direction, 0, # 0 = positive
                      zebra.pc.gate.sel, 0)
    yield from bps.mv(zebra.pc.gate.start, angle_start)
    if image_width != 0:
        yield from bps.mv(zebra.pc.gate.width, num_images * image_width,
                          zebra.pc.gate.step, num_images * image_width + 0.01)
    yield from bps.mv(zebra.pc.gate.num_gates, 1,
                      zebra.pc.pulse.sel, 1,
                      zebra.pc.pulse.start, 0,
                      zebra.pc.pulse.width, (exposure_time_per_image - detector_dead_time) * 1000,
                      zebra.pc.pulse.step, exposure_period_per_image * 1000,
                      zebra.pc.pulse.delay, exposure_period_per_image / 2 * 1000)


def setup_vector_program(vector_program, num_images, angle_start, angle_end,
                         exposure_period_per_image):
    yield from bps.mv(vector_program.num_frames,
                      num_images,
                      vector_program.start.omega,
                      angle_start,
                      vector_program.end.omega,
                      angle_end,
                      vector_program.frame_exptime,
                      exposure_period_per_image*1000.0,
                      vector_program.hold,
                      0)
