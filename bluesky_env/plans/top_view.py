import numpy as np
from scipy.interpolate import interp1d

import bluesky.plans as bp
import bluesky.plan_stubs as bps
from bluesky.utils import FailedStatus
from ophyd.utils import WaitTimeoutError

from start_bs import db, gov_robot
from bluesky_env.devices.top_align import top_aligner_fast, top_aligner_slow, gonio
from bluesky_env.devices.auto_center import work_pos
from bluesky_env.plans.utils import mv_with_retry, mvr_with_retry
import gov_lib

def topview_optimized():

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

        return delta_y, delta_z, omega_min

    # horizontal bump calculation, don't move just yet to avoid disturbing gov
    
    yield from bps.abs_set(top_aligner_slow.topcam.cam_mode, 'coarse_align')
    scan_uid = yield from bp.count([top_aligner_slow.topcam], 1)
    x = db[scan_uid].table()[top_aligner_slow.topcam.cv1.outputs.output8.name][1]
    #x = top_aligner_slow.topcam.cv1.outputs.output8.get()
    delta_x = ((top_aligner_slow.topcam.roi2.size.x.get() / 2) -
               x) / top_aligner_slow.topcam.pix_per_um.get()
    
    

    # update work positions
    yield from bps.abs_set(work_pos.gx, gonio.gx.user_readback.get(), wait=True)
    yield from bps.abs_set(
        work_pos.gpy, top_aligner_fast.gonio_py.user_readback.get(), wait=True
    )
    yield from bps.abs_set(
        work_pos.gpz, top_aligner_fast.gonio_pz.user_readback.get(), wait=True
    )
    yield from bps.abs_set(work_pos.o, 180, wait=True)

    # SE -> TA
    yield from bps.abs_set(top_aligner_fast.target_gov_state, "TA", wait=True)
    yield from bps.abs_set(top_aligner_fast.topcam.cam_mode, "coarse_align")

    try:
        delta_y, delta_z, omega_min = yield from inner_pseudo_fly_scan(
            [top_aligner_fast]
        )
    except (FailedStatus, WaitTimeoutError) as error:
        print("arming problem during coarse alignment...trying again")
        yield from bps.sleep(15)
        gov_lib.setGovRobot(gov_robot, 'SE')
        yield from bps.abs_set(top_aligner_fast.zebra.reset, 1, wait=True)
        yield from bps.sleep(2)
        
        delta_y, delta_z, omega_min = yield from inner_pseudo_fly_scan(
            [top_aligner_fast]
        )

    yield from bps.mvr(gonio.gx, delta_x)
    yield from mvr_with_retry(top_aligner_fast.gonio_py, delta_y)
    yield from mvr_with_retry(top_aligner_fast.gonio_pz, -delta_z)

    # update work positions
    yield from bps.abs_set(work_pos.gx, gonio.gx.user_readback.get(), wait=True)
    yield from bps.abs_set(
        work_pos.gpy, top_aligner_fast.gonio_py.user_readback.get(), wait=True
    )
    yield from bps.abs_set(
        work_pos.gpz, top_aligner_fast.gonio_pz.user_readback.get(), wait=True
    )
    yield from bps.abs_set(work_pos.o, 0, wait=True)

    # TA -> SA
    yield from bps.abs_set(top_aligner_fast.target_gov_state, "SA", wait=True)
    yield from bps.abs_set(top_aligner_fast.topcam.cam_mode, "fine_face")

    try:
        delta_y, delta_z, omega_min = yield from inner_pseudo_fly_scan(
            [top_aligner_fast]
        )
    except (FailedStatus, WaitTimeoutError) as error:
        print("arming problem during fine alignment...trying again")
        yield from bps.sleep(15)
        gov_lib.setGovRobot(gov_robot, 'TA')
        yield from bps.abs_set(top_aligner_fast.zebra.reset, 1, wait=True)
        yield from bps.sleep(2)
        
        delta_y, delta_z, omega_min = yield from inner_pseudo_fly_scan(
            [top_aligner_fast]
        )

    yield from mv_with_retry(top_aligner_fast.gonio_o, omega_min)
    yield from mvr_with_retry(top_aligner_fast.gonio_py, delta_y)
    yield from mvr_with_retry(top_aligner_fast.gonio_pz, -delta_z)
