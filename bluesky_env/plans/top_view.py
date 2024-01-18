import numpy as np
from scipy.interpolate import interp1d

import bluesky.plans as bp
import bluesky.plan_stubs as bps
from bluesky.utils import FailedStatus
from ophyd.utils import WaitTimeoutError
from bluesky.preprocessors import finalize_decorator

from start_bs import db, gov_robot, mount_pos, top_aligner_fast, top_aligner_slow, gonio, work_pos
from bluesky_env.devices.top_align import GovernorError
from bluesky_env.plans.utils import mv_with_retry, mvr_with_retry
import gov_lib
from logging import getLogger

logger = getLogger()

def cleanup_topcam():
    yield from bps.abs_set(top_aligner_slow.topcam.cam.acquire, 1, wait=True)

def inner_pseudo_fly_scan(*args, **kwargs):
    scan_uid = yield from bp.count(*args, **kwargs)
    omegas = db[scan_uid].table()[
        top_aligner_fast.zebra.pos_capt.data.enc4.name
    ][1]

    d = np.pi / 180

    # rot axis calculation, use linear regression
    A_rot = np.matrix(
        [[np.cos(omega * d), np.sin(omega * d), 1] for omega in omegas]
    )

    b_rot = db[scan_uid].table()[top_aligner_fast.topcam.out9_buffer.name][
        1
    ]
    p = (
        np.linalg.inv(A_rot.transpose() * A_rot)
        * A_rot.transpose()
        * np.matrix(b_rot).transpose()
    )

    delta_z_pix, delta_y_pix, rot_axis_pix = p[0], p[1], p[2]
    delta_y, delta_z = (
        delta_y_pix / top_aligner_fast.topcam.pix_per_um.get(),
        delta_z_pix / top_aligner_fast.topcam.pix_per_um.get(),
    )

    # face on calculation
    b = db[scan_uid].table()[top_aligner_fast.topcam.out10_buffer.name][1]

    sample = 300
    f_splines = interp1d(omegas, b)
    b_splines = f_splines(np.linspace(omegas[0], omegas[-1], sample))
    omega_min = np.linspace(omegas[0], omegas[-1], sample)[
        b_splines.argmin()
    ]
    print(f"SPLINES / {omega_min}")

    """
    if (-2000 < delta_y[[0]] < 2000) or (-2000 < delta_z[[0]] < 2000):
        raise ValueError(f"Calculated Delta y or z too large {delta_y=} {delta_z=}")
    """
    

    return delta_y, delta_z, omega_min


@finalize_decorator(cleanup_topcam)
def topview_optimized():

    try:
        # horizontal bump calculation, don't move just yet to avoid disturbing gov
        scan_uid = yield from bp.count([top_aligner_slow], 1)
    except FailedStatus:
        scan_uid = yield from bp.count([top_aligner_slow], 1)

    x = db[scan_uid].table()[top_aligner_slow.topcam.cv1.outputs.output8.name][1]
    delta_x = ((top_aligner_slow.topcam.roi2.size.x.get() / 2) -
               x) / top_aligner_slow.topcam.pix_per_um.get()

    # update work positions
    yield from set_TA_work_pos(delta_x=delta_x)

    # SE -> TA
    yield from bps.abs_set(top_aligner_fast.target_gov_state, "TA", wait=True)
    yield from bps.abs_set(top_aligner_fast.topcam.cam_mode, 'coarse_align')
    yield from bps.sleep(0.1)

    try:
        delta_y, delta_z, omega_min = yield from inner_pseudo_fly_scan(
            [top_aligner_fast]
        )
    except (FailedStatus, WaitTimeoutError, GovernorError, ValueError) as error:
        print(f"Error: {error}")
        print("arming problem during coarse alignment...trying again")

        yield from bps.sleep(15)
        yield from bps.abs_set(gov_robot, 'SE', wait=True)
        yield from bps.abs_set(top_aligner_fast.zebra.reset, 1, wait=True)
        yield from bps.sleep(4)  # 2-3 sec will disarm zebra after reset

        delta_y, delta_z, omega_min = yield from inner_pseudo_fly_scan(
            [top_aligner_fast]
        )

    yield from mvr_with_retry(top_aligner_fast.gonio_py, delta_y)
    yield from mvr_with_retry(top_aligner_fast.gonio_pz, -delta_z)

    # update work positions
    yield from set_SA_work_pos(delta_y, delta_z)

    # TA -> SA
    yield from bps.abs_set(top_aligner_fast.target_gov_state, "SA", wait=True)
    yield from bps.abs_set(top_aligner_fast.topcam.cam_mode, "fine_face")
    yield from bps.sleep(0.1)

    try:
        delta_y, delta_z, omega_min = yield from inner_pseudo_fly_scan(
            [top_aligner_fast]
        )
    except (FailedStatus, WaitTimeoutError, GovernorError, ValueError) as error:
        print(f"Error: {error}")
        print("arming problem during fine alignment...trying again")
        yield from bps.sleep(15)
        # update work positions for TA reset
        yield from set_TA_work_pos()
        yield from bps.abs_set(gov_robot, 'TA', wait=True)
        yield from bps.abs_set(top_aligner_fast.zebra.reset, 1, wait=True)

        # update work positions for TA -> SA retry
        yield from set_SA_work_pos(delta_y, delta_z)
        yield from bps.sleep(4)  # 2-3 sec will disarm zebra after reset

        delta_y, delta_z, omega_min = yield from inner_pseudo_fly_scan(
            [top_aligner_fast]
        )

    yield from mv_with_retry(top_aligner_fast.gonio_o, omega_min)
    yield from mvr_with_retry(top_aligner_fast.gonio_py, delta_y)
    yield from mvr_with_retry(top_aligner_fast.gonio_pz, -delta_z)

    set_SA_work_pos(delta_y, delta_z, gonio.py.user_readback.get(), gonio.pz.user_readback.get(), omega=gonio.o.user_readback.get())

def set_TA_work_pos(delta_x=None):
    if delta_x:
        yield from bps.abs_set(work_pos.gx, mount_pos.gx.get() + delta_x, wait=True)
    yield from bps.abs_set(
        work_pos.gpy, mount_pos.py.get(), wait=True
    )
    yield from bps.abs_set(
        work_pos.gpz, mount_pos.pz.get(), wait=True
    )
    yield from bps.abs_set(work_pos.o, 180, wait=True)

def set_SA_work_pos(delta_y, delta_z, current_y=None, current_z= None, omega=0):
    if current_y is None:
        current_y = mount_pos.py.get()
    if current_z is None:
        current_z = mount_pos.pz.get()
    yield from bps.abs_set(
        work_pos.gpy, current_y + delta_y, wait=True
    )
    yield from bps.abs_set(
        work_pos.gpz, current_z - delta_z, wait=True
    )
    yield from bps.abs_set(work_pos.o, omega, wait=True)
