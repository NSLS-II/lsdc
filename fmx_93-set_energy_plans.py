# Plans to set beamline energy

# TODO: rework it to use ophyd devices/components instead of epics.caget(...).

import bluesky.preprocessors as bpp
import bluesky.plans as bp
import bluesky.plan_stubs as bps
import epics
import pandas as pd
import numpy as np


# Helper functions for set_energy and alignment

def find_peak(det, mot, start, stop, steps):
    print(f"Scanning {mot.name} vs {det.name}...")

    uid = yield from bp.relative_scan([det], mot, start, stop, steps)

    sp = '_gap_user_setpoint' if mot is ivu_gap else '_user_setpoint'
    output = '_sum_all' if det is bpm1 else ''
    data = np.array(db[uid].table()[[det.name+output, mot.name+sp]])[1:]

    peak_idx = np.argmax(data[:, 0])
    peak_x = data[peak_idx, 1]
    peak_y = data[peak_idx, 0]

    if mot is ivu_gap:
        m = mot.gap
    else:
        m = mot
    print(f"Found peak for {m.name} at {peak_x} {m.egu} [BPM reading {peak_y}]")
    return peak_x, peak_y

# TODO Use blStrGet()
LUT_fmt = "XF:17ID-ES:FMX{{Misc-LUT:{}}}{}-Wfm"
LGP_fmt = "XF:17ID-ES:FMX{{Misc-LGP:{}}}Pos-SP"

# AMX/FMX
LUT_valid = (ivu_gap.gap, hdcm.g, hdcm.r, hdcm.p, hfm.y, hfm.x, hfm.pitch, kbm.hy, kbm.vx, atten)
LGP_valid = (kbm.hp, kbm.hx, kbm.vp, kbm.vy)

LUT_valid_names = [m.name for m in LUT_valid] + ['ivu_gap_off']
LGP_valid_names = [m.name for m in LGP_valid]

def read_lut(name):
    """
    Reads the LookUp table values for a specific motor
    """
    if name not in LUT_valid_names:
        raise ValueError('name must be one of {}'.format(LUT_valid_names))

    x, y = [epics.caget(LUT_fmt.format(name, axis)) for axis in 'XY']
    return pd.DataFrame({'Energy':x, 'Position': y})


def write_lut(name, energy, position):
    """
    Writes to the LookUp table for a specific motor
    """
    if name not in LUT_valid_names:
        raise ValueError('name must be one of {}'.format(LUT_valid_names))

    if len(energy) != len(position):
        raise ValueError('energy and position must have the same number of points')

    epics.caput(LUT_fmt.format(name, 'X'), energy)
    epics.caput(LUT_fmt.format(name, 'Y'), position)


def read_lgp(name):
    """
    Reads the Last Good Position value for a specific motor
    """
    if name not in LGP_valid_names:
        raise ValueError('name must be one of {}'.format(LGP_valid_names))

    return epics.caget(LGP_fmt.format(name))

def write_lgp(name, position):
    """
    Writes to the Last Good Position value for a specific motor
    """
    if name not in LGP_valid_names:
        raise ValueError('name must be one of {}'.format(LGP_valid_names))

    return epics.caput(LGP_fmt.format(name), position)
    
    
def setE_motors_FMX(energy):
    """
    Sets undulator, HDCM, HFM and KB settings for a certain energy from a lookup table

    energy: Photon energy [eV]

    Lookup tables and variables are set in a settings notebook:
    settings/set_energy setup FMX.ipynb

    Examples:
    setE_motors_FMX(12660)
    """
    
    # (FMX specific)
    LUT = {m: [epics.caget(LUT_fmt.format(m.name, axis))
           for axis in 'XY']
           for m in (ivu_gap.gap, hdcm.g, hdcm.r, hdcm.p, hfm.y, hfm.x, hfm.pitch, kbm.hy, kbm.vx)}

    LUT_offset = [epics.caget(LUT_fmt.format('ivu_gap_off', axis)) for axis in 'XY']

    LGP = {m: epics.caget(LGP_fmt.format(m.name))
           for m in (kbm.hp, kbm.hx, kbm.vp, kbm.vy)}

    # Open Slits 1 (FMX specific)
    yield from bps.mv(
        slits1.x_gap, 3000,
        slits1.y_gap, 2000
    )
    
    # Remove CRLs if going to energy < 9 keV (FMX specific)
    if energy < 9001:
        set_beamsize('V0','H0')
    
    # Lookup Table
    def lut(motor):
        if motor is ivu_gap:
            return motor, np.interp(energy, *LUT[motor.gap])
        else:
            return motor, np.interp(energy, *LUT[motor])
    
    # Last Good Position
    def lgp(motor):
        return motor, LGP[motor]
    
    # (FMX specific)
    yield from bps.mv(
        *lut(ivu_gap),   # Set IVU Gap interpolated position
        hdcm.e, energy,  # Set Bragg Energy pseudomotor
        *lut(hdcm.g),    # Set DCM Gap interpolated position
        *lut(hdcm.r),    # Set DCM Roll interpolated position # MF 20180331
        *lut(hdcm.p),    # Set Pitch interpolated position

        # Set HFM from interpolated positions
        *lut(hfm.x),
        *lut(hfm.y),
        *lut(hfm.pitch),

        # Set KB from interpolated positions
        *lut(kbm.vx),
        *lut(kbm.hy),

        # Set KB from known good setpoints
        *lgp(kbm.vy), *lgp(kbm.vp),
        *lgp(kbm.hx), *lgp(kbm.hp)
    )    
    
    
def dcm_rock(dcm_p_range=0.03, dcm_p_points=51, logging=True, altDetector=False):
    """
    Scan DCM crystal 2 pitch to maximize flux on BPM1
    dcm_rock() runs both with the AMX VDCM and the FMX HDCM

    Parameters
    ----------
    
    Optional arguments:
    dcm_p_range: DCM rocking curve range [mrad]. Default 0.03 mrad
    dcm_p_points: DCM rocking curve points. Default 51
    altDetector: If True, uses alternate detector, BPM1 at AMX and Keithley at FMX

    Examples
    --------
    
    RE(dcm_rock())
    RE(dcm_rock(altDetector = True))
    RE(dcm_rock(dcm_p_range=0.035, dcm_p_points=71))
    """
    blStr = blStrGet()
    if blStr == -1: return -1
    
    if blStr == 'AMX':
        rock_mot = vdcm.p
        rock_det = bpm1 if altDetector is True else keithley
    elif blStr == 'FMX':
        rock_mot = hdcm.p
        rock_det = keithley if altDetector is True else bpm1
    
    energy = get_energy()
        
    LUT = {m: [epics.caget(LUT_fmt.format(m.name, axis))
           for axis in 'XY']
           for m in (rock_mot, )}

    # Lookup Table
    def lut(motor):
        return motor, np.interp(energy, *LUT[motor])

    yield from bps.mv(
        *lut(rock_mot)    # Set Pitch interpolated position
    )

    # Setup plots
    ax1 = plt.subplot(111)
    ax1.grid(True)
    plt.tight_layout()
    
    # Decorate find_peaks to play along with our plot and plot the peak location
    def find_peak_inner(detector, motor, start, stop, num, ax):
        if detector == bpm1:
            det_name = detector.name+'_sum_all'
        else:
            det_name = detector.name                
        mot_name = motor.name+'_user_setpoint'

        @bpp.subs_decorator(LivePlot(det_name, mot_name, ax=ax))
        def inner():
            peak_x, peak_y = yield from find_peak(detector, motor, start, stop, num)
            ax.plot([peak_x], [peak_y], 'or')
            return peak_x, peak_y
        return inner()

    # Scan DCM Pitch
    peak_x, peak_y = yield from find_peak_inner(rock_det, rock_mot, -dcm_p_range, dcm_p_range, dcm_p_points, ax1)
    yield from bps.mv(rock_mot, peak_x)
    
    # (FMX specific)
    if logging:
        print('Energy = {:.1f} eV'.format(energy))       
        print('HDCM cr2 pitch = {:.3f} mrad'.format(rock_mot.user_readback.get()))
        if rock_det == bpm1:
            print('BPM1 sum = {:.4g} A'.format(bpm1.sum_all.get()))
        elif  rock_det == keithley:
            time.sleep(2.0)  # Range switching is slow
            print('Keithley current = {:.4g} A'.format(keithley.get()))
        
    #plt.close()
        
    
def ivu_gap_scan(start, end, steps, detector=bpm1, goToPeak=True):
    """
    Scans the IVU21 gap against a detector, and moves the gap to the peak plus a
    energy dependent look-up table set offset

    Parameters
    ----------
    
    start: float
        The starting position (um) of the VU21 undulator gap scan
    
    end: float
        The end position (um) of the VU21 undulator gap scan
        
    steps: int
        Number of steps in the scan
    
    detector: ophyd detector
        The ophyd detector for the scan. Default is bpm1. Only setup up for the quad BPMs right now
    
    goToPeak: boolean
        If True, go to the peak plus energy-tabulated offset. If False, go back to pre-scan value.
    
    Examples
    --------
    
    RE(ivu_gap_scan(7350, 7600, 70))
    RE(ivu_gap_scan(7350, 7600, 70, goToPeak=False))
    RE(ivu_gap_scan(7350, 7600, 70, detector=bpm4))
    """
        
    energy = get_energy()
    
    motor=ivu_gap
    if start-1 < motor.gap.low_limit:
        start = motor.gap.low_limit + 1
        print('start violates lowest limit, set to %.1f' % start + ' um')
    
    LUT_offset = [epics.caget(LUT_fmt.format('ivu_gap_off', axis)) for axis in 'XY']
    
    # Setup plots
    ax = plt.subplot(111)
    ax.grid(True)
    plt.tight_layout()

    # Decorate find_peaks to play along with our plot and plot the peak location
    def find_peak_inner(detector, motor, start, stop, num, ax):
        det_name = detector.name+'_sum_all'
        mot_name = motor.gap.name+'_user_setpoint' if motor is ivu_gap else motor.name+'_user_setpoint'

        # Prevent going below the lower limit or above the high limit
        if motor is ivu_gap:
            step_size = (stop - start) / (num - 1)
            while motor.gap.user_setpoint.get() + start < motor.gap.low_limit:
                start += 5*step_size
                stop += 5*step_size

            while motor.gap.user_setpoint.get() + stop > motor.gap.high_limit:
                start -= 5*step_size
                stop -= 5*step_size

        @bpp.subs_decorator(LivePlot(det_name, mot_name, ax=ax))
        def inner():
            peak_x, peak_y = yield from find_peak(detector, motor, start, stop, num)
            ax.plot([peak_x], [peak_y], 'or')
            return peak_x, peak_y
        return inner()
    
    # Remember pre-scan value
    gapPreStart=motor.gap.user_readback.get()
    
    # Move to start
    yield from bps.mv(motor, start)
    
    # Scan IVU Gap
    peak_x, peak_y = yield from find_peak_inner(detector, ivu_gap, 0, (end-start), steps, ax)
    
    # Go to peak
    if goToPeak==True:
        peakoffset_x = (peak_x + np.interp(energy, *LUT_offset))
        yield from bps.mv(ivu_gap, peakoffset_x)
        print('Gap set to peak + tabulated offset: %.1f' % peakoffset_x + ' um')
    else:
        yield from bps.mv(ivu_gap, gapPreStart)
        print('Gap set to pre-scan value: %.1f' % gapPreStart + ' um')
    
    #plt.close()

    
def setE(energy,
         dcm_p_range=0.03, dcm_p_points=51, altDetector=False,
         ivuGapStartOff=70, ivuGapEndOff=70, ivuGapSteps=31,
         transSet='All', beamCenterAlign=True):
    """
    Automated photon energy change. Master function calling four subroutines:
    * setE_motors_FMX():    Set photon delivery system motor positions for a chosen energy
    * dcm_rock():           Go to peak of monochromator rocking curve
    * ivu_gap_scan():       Go to peak of undulator gap
    * beam_center_align():  Set LSDC crosshair to beam center
                            Move rotation axis to beam heightS
                            Set governor Gonio Y Work position
    
    Requirements
    ------------
    Governor in state SA
    FOE and hutch photon shutter open
    
    
    Parameters
    ----------
    
    energy: Photon energy [eV]
    
    dcm_p_range: Scan range of DCM Crystal 2 Pitch [mrad], default = 0.03
    dcm_p_points: Number of scan points of SCM rocking curve, default = 51
    altDetector: Rocking curve to use alternate detector between BPM1 and endstation diode, default = False
    
    ivuGapStartOff: IVU gap scan start offset from tabulated position [um], default = 70
    ivuGapEndOff: IVU gap scan end offset from tabulated position [um], default = 70
    ivuGapSteps: IVU gap scan steps, default = 31
    
    transSet: FMX only: Set to 'RI' if there is a problem with the BCU attenuator.
              FMX only: Set to 'BCU' if there is a problem with the RI attenuator.
              Set to 'None' if there are problems with all = attenuators.
              Operator then has to choose a flux by hand that will not saturate scinti
              default = 'All'
    
    beamCenterAlign: Set to False to skip beam_center_align() step (like the old set_energy() routine)
                     Default True
    
    Examples
    --------
    
    RE(setE(7110))
    RE(setE(10000, transSet='None'))
    RE(setE(12660, transSet='RI'))
    RE(setE(20000, ivuGapStartOff=100, ivuGapEndOff=150, ivuGapSteps=91))
    RE(setE(9000, beamCenterAlign=False))
    """
    
    # Store initial Slit 1 gap positions
    slits1XGapOrg = slits1.x_gap.user_readback.get()
    slits1YGapOrg = slits1.y_gap.user_readback.get()
    
    print('Setting FMX motor positions')
    try:
        yield from setE_motors_FMX(energy)
    except:
        print('setE_motors_FMX() failed')
        raise
    else:
        print('setE_motors_FMX() successful')
        time.sleep(1)
    
    # Check for pre-conditions for dcm_rock() and ivu_gap_scan()
    if shutter_foe.status.get():
        print('FOE shutter closed. Has to be open for this to work. Exiting')
        return -1
        
    print('Rocking monochromator')
    yield from dcm_rock(dcm_p_range=dcm_p_range, dcm_p_points=dcm_p_points, altDetector=altDetector)
    time.sleep(1)
        
    print('Scanning undulator gap')
    start = ivu_gap.gap.user_readback.get() - ivuGapStartOff
    end = ivu_gap.gap.user_readback.get() + ivuGapEndOff
    try:
        yield from ivu_gap_scan(start, end, ivuGapSteps, goToPeak=True)
    except:
        print('ivu_gap_scan() failed')
        raise
    else:
        print('ivu_gap_scan() successful')
        time.sleep(1)
    
    if beamCenterAlign:
        # Check for pre-conditions for beam_center_align()
        if shutter_hutch_c.status.get():
            print('Experiment hutch shutter closed. Has to be open for this to work. Exiting')
            return -1
        if not govStatusGet('SA'):
            print('Not in Governor state SA, exiting')
            return -1
        
        print('Aligning beam center')
        yield from beam_center_align(transSet=transSet)
    
    # Restore initial Slit 1 gap positions
    yield from bps.mv(slits1.x_gap, slits1XGapOrg)  # Move Slit 1 X to original position
    yield from bps.mv(slits1.y_gap, slits1YGapOrg)  # Move Slit 1 Y to original position
    
