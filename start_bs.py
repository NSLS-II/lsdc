#!/opt/conda_envs/lsdc-server-2023-2-latest/bin/ipython -i
# import asyncio
from ophyd import *
from ophyd.mca import (Mercury1, SoftDXPTrigger)
from ophyd import Device, EpicsMotor, EpicsSignal, EpicsSignalRO
from mxtools.zebra import Zebra
from mxtools.eiger import EigerSingleTriggerV26, set_eiger_defaults
import os
from mxtools.governor import _make_governors
from ophyd.signal import EpicsSignalBase
EpicsSignalBase.set_defaults(timeout=10, connection_timeout=10)  # new style
from mxbluesky.devices import (WorkPositions, TwoClickLowMag, LoopDetector, MountPositions, 
                                 TopAlignerFast, TopAlignerSlow, GoniometerStack)

#12/19 - author unknown. DAMA can help
"""
# Subscribe metadatastore to documents.
# If this is removed, data is not saved to metadatastore.
import metadatastore.commands
from bluesky.global_state import gs
gs.RE.subscribe_lossless('all', metadatastore.commands.insert)
from bluesky.callbacks.broker import post_run
# At the end of every run, verify that files were saved and
# print a confirmation message.
from bluesky.callbacks.broker import verify_files_saved
gs.RE.subscribe('stop', post_run(verify_files_saved))
"""
# Import matplotlib and put it in interactive mode.
import matplotlib.pyplot as plt
plt.ion()

# Register bluesky IPython magics.
#from bluesky.magics import BlueskyMagics
#get_ipython().register_magics(BlueskyMagics)

import bluesky.plans as bp

from bluesky.run_engine import RunEngine
from bluesky.utils import get_history, PersistentDict
RE = RunEngine()
beamline = os.environ["BEAMLINE_ID"]
from nslsii import configure_kafka_publisher
configure_kafka_publisher(RE, beamline)
configdir = os.environ['CONFIGDIR']
RE.md = PersistentDict('%s%s_bluesky_config' % (configdir, beamline))
from databroker import Broker
db = Broker.named(beamline)

RE.subscribe(db.insert)

from bluesky.log import config_bluesky_logging
config_bluesky_logging()
#from bluesky.utils import ts_msg_hook
#RE.msg_hook = ts_msg_hook
# from bluesky.callbacks.best_effort import BestEffortCallback
# bec = BestEffortCallback()
# RE.subscribe(bec)

# convenience imports
# from ophyd.commands import *
from bluesky.callbacks import *
# from bluesky.spec_api import *
# from bluesky.global_state import gs, abort, stop, resume
# from databroker import (DataBroker as db, get_events, get_images,
#                                                 get_table, get_fields, restream, process)

# RE = gs.RE  # convenience alias
#rest is hugo
abort = RE.abort
resume = RE.resume
stop = RE.stop

# the following lines should not be needed as these should be persisted
#RE.md['group'] = beamline
#RE.md['beamline_id'] = beamline.upper()

# loop = asyncio.get_event_loop()
# loop.set_debug(False)



from ophyd import (SingleTrigger, ProsilicaDetector,
                   ImagePlugin, StatsPlugin, ROIPlugin)

from ophyd import Component as Cpt

class ABBIXMercury(Mercury1, SoftDXPTrigger):
    pass

class MD2Positioner(PVPositioner):
    setpoint = Cpt(EpicsSignal, 'Position', name='setpoint')
    readback = Cpt(EpicsSignal, 'Position', name='readback')
    state = Cpt(EpicsSignalRO, 'State', name='state')
    done = Cpt(EpicsSignalRO, 'State', name='done')
    precision = Cpt(EpicsSignalRO, 'Precision', name='precision')
    done_value = 4 # MD2 Enum, 4 = Ready
    # TODO: Add limits, settle_time, timeout or defaults for each

    def val(self):
        return self.get().readback

class FrontLightDevice(Device):
    control = Cpt(EpicsSignal, 'FrontLightIsOn', name='control')
    factor = Cpt(EpicsSignal, 'FrontLightFactor', name='factor')
    level = Cpt(EpicsSignal, 'FrontLightLevel', name='level')
    
    def is_on(self):
        return self.control.get() == 1

    def turn_on(self):
        self.control.set(1)

    def turn_off(self):
        self.control.set(0)

    def set_factor(self, factor):
        self.factor.set(factor)
    
    def set_level(self, level):
        self.level.set(level)

class BeamstopDevice(Device):
    distance = Cpt(MD2Positioner, "BeamstopDistance", name="distance")
    x = Cpt(MD2Positioner, "BeamstopX", name="x")
    y = Cpt(MD2Positioner, "BeamstopY", name="y")
    z = Cpt(MD2Positioner, "BeamstopZ", name="z")
    position = Cpt(EpicsSignal, "BeamstopPosition", name="position")

class MD2SimpleHVDevice(Device):
    horizontal = Cpt(MD2Positioner, "HVHorizontal", name="horizontal")
    vertical = Cpt(MD2Positioner, "HVVertical", name="vertical")
    position = Cpt(EpicsSignal, "HVPosition", name="position")
    # Current aperture/scintillator/capillary predifined position.
    # Enum: the aperture position:
    # 0: PARK, under cover.
    # 1: BEAM, selected aperture aligned with beam.
    # 2: OFF, just below the OAV.
    # 3: UNKNOWN, not in a predefined position (this cannot be set).

class MD2Device(Device):
    omega = Cpt(MD2Positioner, 'Omega',name='omega')
    x = Cpt(MD2Positioner, 'AlignmentX',name='x')
    y = Cpt(MD2Positioner, 'AlignmentY',name='y')
    z = Cpt(MD2Positioner, 'AlignmentZ',name='z')
    cx = Cpt(MD2Positioner, 'CentringX',name='cx')
    cy = Cpt(MD2Positioner, 'CentringY',name='cy')
    phase_index = Cpt(EpicsSignalRO, 'CurrentPhaseIndex',name='phase_index')
    detector_state = Cpt(EpicsSignal, 'DetectorState',name='det_state')
    detector_gate_pulse_enabled = Cpt(EpicsSignal, 'DetectorGatePulseEnabled',name='det_gate_pulse_enabled')

    def standard_scan(self, 
            frame_number=0, # int: frame ID just for logging purposes.
            num_images=1, # int: number of frames. Needed solely when the detector use gate enabled trigger.
            start_angle=0, # double: angle (deg) at which the shutter opens and omega speed is stable.
            scan_range=1, # double: omega relative move angle (deg) before closing the shutter.
            exposure_time=0.1, # double: exposure time (sec) to control shutter command.
            num_passes=1 # int: number of moves forward and reverse between start angle and stop angle
            ):
        command = 'startScanEx2'
        if start_angle is None:
            start_angle=self.omega.get()
        return self.exporter.cmd(command, [frame_number, num_images, start_angle, scan_range, exposure_time, num_passes])

    def vector_scan(self,
            start_angle=None, # double: angle (deg) at which the shutter opens and omega speed is stable.
            scan_range=10, # double: omega relative move angle (deg) before closing the shutter.
            exposure_time=1, # double: exposure time (sec) to control shutter command.
            start_y=None, # double: PhiY axis position at the beginning of the exposure.
            start_z=None, # double: PhiZ axis position at the beginning of the exposure.
            start_cx=None, # double: CentringX axis position at the beginning of the exposure.
            start_cy=None, # double: CentringY axis position at the beginning of the exposure.
            stop_y=None, # double: PhiY axis position at the end of the exposure.
            stop_z=None, # double: PhiZ axis position at the end of the exposure.
            stop_cx=None, # double: CentringX axis position at the end of the exposure.
            stop_cy=None, # double: CentringY axis position at the end of the exposure.
            ):
        command = 'startScan4DEx'
        if start_angle is None:
            start_angle = self.omega.val()
        if start_y is None:
            start_y = self.y.val()
        if start_z is None:
            start_z = self.z.val()
        if start_cx is None:
            start_cx = self.cx.val()
        if start_cy is None:
            start_cy = self.cy.val()
        if stop_y is None:
            stop_y = self.y.val()+0.1
        if stop_z is None:
            stop_z = self.z.val()+0.1
        if stop_cx is None:
            stop_cx = self.cx.val()+0.1
        if stop_cy is None:
            stop_cy = self.cy.val()+0.1

        # List of scan parameters values, comma separated. The axes start values define the beginning
        # of the exposure, that is when all the axes have a steady speed and when the shutter/detector
        # are triggered.
        # The axes stop values are for the end of detector exposure and define the position at the
        # beginning of the deceleration.
        # Inputs names: "start_angle", "scan_range", "exposure_time", "start_y", "start_z", "start_cx",
        # "start_cy", "stop_y", "stop_z", "stop_cx", "stop_cy"
        param_list = [start_angle, scan_range, exposure_time,
                start_y, start_z, start_cx, start_cy, 
                stop_y, stop_z, stop_cx, stop_cy]
        return self.exporter.cmd(command, param_list)

    def raster_scan(self, 
            omega_range=0, # double: omega relative move angle (deg) before closing the shutter.
            line_range=0.1, # double: horizontal range of the grid (mm).
            total_uturn_range=0.1, # double: vertical range of the grid (mm).
            start_omega=None, # double: angle (deg) at which the shutter opens and omega speed is stable.
            start_y=None, # double: PhiY axis position at the beginning of the exposure.
            start_z=None, # double: PhiZ axis position at the beginning of the exposure.
            start_cx=None, # double: CentringX axis position at the beginning of the exposure.
            start_cy=None, # double: CentringY axis position at the beginning of the exposure.
            number_of_lines=5, # int: number of frames on the vertical range.
            frames_per_line=5, # int: number of frames on the horizontal range.
            exposure_time=1.2, # double: exposure time (sec) to control shutter command. +1, based on the exaples given
            invert_direction=True, # boolean: true to enable passes in the reverse direction.
            use_table_centering=True, # boolean: true to use the centring table to do the pitch movements.
            use_fast_mesh_scans=True # boolean: true to use the fast raster scan if available (power PMAC).
            ):

        command = 'startRasterScanEx'
        if start_omega is None:
            start_omega = self.omega.val()
        if start_y is None:
            start_y = self.y.val()
        if start_z is None:
            start_z = self.z.val()
        if start_cx is None:
            start_cx = self.cx.val()
        if start_cy is None:
            start_cy = self.cy.val()
        # List of scan parameters values, "/t" separated. The axes start values define the beginning
        # of the exposure, that is when all the axes have a steady speed and when the shutter/detector
        # are triggered.
        # The axes stop values are for the end of detector exposure and define the position at the
        # beginning of the deceleration.
        # Inputs names: "omega_range", "line_range", "total_uturn_range", "start_omega", "start_y",
        # "start_z", "start_cx", "start_cy", "number_of_lines", "frames_per_lines", "exposure_time",
        # "invert_direction", "use_centring_table", "use_fast_mesh_scans"
        param_list = [omega_range, line_range, total_uturn_range, start_omega, start_y, start_z,
                start_cx, start_cy, number_of_lines, frames_per_line, exposure_time, 
                invert_direction, use_table_centering, use_fast_mesh_scans]
        return self.exporter.cmd(command, param_list)

class ShutterDevice(Device):
    control = Cpt(EpicsSignal, '{MD2}:FastShutterIsOpen', name='control') # PV to send control signal
    pos_opn = Cpt(EpicsSignalRO, '{Gon:1-Sht}Pos:Opn-I', name='pos_opn')
    pos_cls = Cpt(EpicsSignalRO, '{Gon:1-Sht}Pos:Cls-I', name='pos_cls')

    def is_open(self):
        return self.control.get() == 1 #self.pos_opn.get()

    def open_shutter(self):
        self.control.set(1)#self.pos_opn.get()) iocs are down, so just setting it to 1

    def close_shutter(self):
        self.control.set(0)#self.pos_cls.get())

class VerticalDCM(Device):
    b = Cpt(EpicsMotor, '-Ax:B}Mtr')
    g = Cpt(EpicsMotor, '-Ax:G}Mtr')
    p = Cpt(EpicsMotor, '-Ax:P}Mtr')
    r = Cpt(EpicsMotor, '-Ax:R}Mtr')
    e = Cpt(EpicsMotor, '-Ax:E}Mtr')
    w = Cpt(EpicsMotor, '-Ax:W}Mtr')

class StandardProsilica(SingleTrigger, ProsilicaDetector):
    image = Cpt(ImagePlugin, 'image1:')
    roi1 = Cpt(ROIPlugin, 'ROI1:')
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats5 = Cpt(StatsPlugin, 'Stats5:')

def filter_camera_data(camera):
    camera.read_attrs = ['stats1', 'stats5']
    camera.stats1.read_attrs = ['total', 'centroid']
    camera.stats5.read_attrs = ['total', 'centroid']

class SampleXYZ(Device):
    x = Cpt(EpicsMotor, ':X}Mtr')
    y = Cpt(EpicsMotor, ':Y}Mtr')
    z = Cpt(EpicsMotor, ':Z}Mtr')
    omega = Cpt(EpicsMotor, ':O}Mtr')

if (beamline=="amx"):
    mercury = ABBIXMercury('XF:17IDB-ES:AMX{Det:Mer}', name='mercury')
    mercury.read_attrs = ['mca.spectrum', 'mca.preset_live_time', 'mca.rois.roi0.count',
                                            'mca.rois.roi1.count', 'mca.rois.roi2.count', 'mca.rois.roi3.count']
    vdcm = VerticalDCM('XF:17IDA-OP:AMX{Mono:DCM', name='vdcm')
    zebra = Zebra('XF:17IDB-ES:AMX{Zeb:2}:', name='zebra')
    eiger = EigerSingleTriggerV26('XF:17IDB-ES:AMX{Det:Eig9M}', name='eiger', beamline=beamline)
    from mxtools.vector_program import VectorProgram
    vector_program = VectorProgram('XF:17IDB-ES:AMX{Gon:1-Vec}', name='vector_program')
    from mxtools.flyer import MXFlyer
    flyer = MXFlyer(vector_program, zebra, eiger)
    from mxtools.raster_flyer import MXRasterFlyer
    raster_flyer = MXRasterFlyer(vector_program, zebra, eiger)
    samplexyz = SampleXYZ("XF:17IDB-ES:AMX{Gon:1-Ax", name="samplexyz")

    from embl_robot import EMBLRobot
    robot = EMBLRobot()
    govs = _make_governors("XF:17IDB-ES:AMX", name="govs")
    gov_robot = govs.gov.Robot

    back_light = EpicsSignal(read_pv="XF:17DB-ES:AMX{BL:1}Ch1Value",name="back_light")
    back_light_range = (0, 100)

    work_pos = WorkPositions("XF:17IDB-ES:AMX", name="work_pos")
    mount_pos = MountPositions("XF:17IDB-ES:AMX", name="mount_pos")
    two_click_low = TwoClickLowMag("XF:17IDB-ES:AMX{Cam:6}", name="two_click_low")
    gonio = GoniometerStack("XF:17IDB-ES:AMX{Gon:1", name="gonio")
    loop_detector = LoopDetector(name="loop_detector")
    top_aligner_fast = TopAlignerFast(name="top_aligner_fast", gov_robot=gov_robot)
    top_aligner_slow = TopAlignerSlow(name="top_aligner_slow")
    

elif beamline == "fmx":  
    mercury = ABBIXMercury('XF:17IDC-ES:FMX{Det:Mer}', name='mercury')
    mercury.read_attrs = ['mca.spectrum', 'mca.preset_live_time', 'mca.rois.roi0.count',
                                            'mca.rois.roi1.count', 'mca.rois.roi2.count', 'mca.rois.roi3.count']
    vdcm = VerticalDCM('XF:17IDA-OP:FMX{Mono:DCM', name='vdcm')
    zebra = Zebra('XF:17IDC-ES:FMX{Zeb:3}:', name='zebra')
    eiger = EigerSingleTriggerV26('XF:17IDC-ES:FMX{Det:Eig16M}', name='eiger', beamline=beamline)
    from mxtools.vector_program import VectorProgram
    vector_program = VectorProgram('XF:17IDC-ES:FMX{Gon:1-Vec}', name='vector_program')
    from mxtools.flyer import MXFlyer
    flyer = MXFlyer(vector_program, zebra, eiger)
    from mxtools.raster_flyer import MXRasterFlyer
    raster_flyer = MXRasterFlyer(vector_program, zebra, eiger)
    samplexyz = SampleXYZ("XF:17IDC-ES:FMX{Gon:1-Ax", name="samplexyz")

    from embl_robot import EMBLRobot
    robot = EMBLRobot()
    govs = _make_governors("XF:17IDC-ES:FMX", name="govs")
    gov_robot = govs.gov.Robot

    back_light = EpicsSignal(read_pv="XF:17DC-ES:FMX{BL:1}Ch1Value",name="back_light")
    back_light_range = (0, 100)

    work_pos = WorkPositions("XF:17IDC-ES:FMX", name="work_pos")
    mount_pos = MountPositions("XF:17IDC-ES:FMX", name="mount_pos")
    two_click_low = TwoClickLowMag("XF:17IDC-ES:FMX{Cam:7}", name="two_click_low")
    gonio = GoniometerStack("XF:17IDC-ES:FMX{Gon:1", name="gonio")
    loop_detector = LoopDetector(name="loop_detector")
    top_aligner_fast = TopAlignerFast(name="top_aligner_fast", gov_robot=gov_robot)
    top_aligner_slow = TopAlignerSlow(name="top_aligner_slow")

    import setenergy_lsdc

elif beamline=="nyx":
    mercury = ABBIXMercury('XF:17IDC-ES:FMX{Det:Mer}', name='mercury')
    mercury.read_attrs = ['mca.spectrum', 'mca.preset_live_time', 'mca.rois.roi0.count',
                                            'mca.rois.roi1.count', 'mca.rois.roi2.count', 'mca.rois.roi3.count']
    vdcm = VerticalDCM('XF:17IDA-OP:FMX{Mono:DCM', name='vdcm')
    zebra = Zebra('XF:19IDC-ES{Zeb:1}:', name='zebra')
    from nyxtools.vector import VectorProgram
    vector = VectorProgram("XF:19IDC-ES{Gon:1-Vec}", name="vector")
    from mxtools.eiger import EigerSingleTriggerV26
    detector = EigerSingleTriggerV26("XF:19ID-ES:NYX{Det:Eig9M}", name="detector", beamline=beamline)
    from nyxtools.flyer_eiger2 import NYXEiger2Flyer
    flyer = NYXEiger2Flyer(vector, zebra, detector)
    from nyxtools.nyx_raster_flyer import NYXRasterFlyer
    raster_flyer = NYXRasterFlyer(vector, zebra, detector)

    from nyxtools.isara_robot import IsaraRobotDevice
    from denso_robot import OphydRobot
    ophyd_robot = IsaraRobotDevice("XF19IDC-ES{Rbt:1}", name="robot")
    robot = OphydRobot(ophyd_robot) # OphydRobot is the robot_lib API-compatible object
    govs = _make_governors("XF:19IDC-ES", name="govs")
    gov_robot = govs.gov.Robot

    md2 = MD2Device("XF:19IDC-ES{MD2}:", name="md2")
    shutter = ShutterDevice('XF:19IDC-ES{MD2}:', name='shutter')
    beamstop = BeamstopDevice('XF:19IDC-ES{MD2}:', name='beamstop')
    front_light = FrontLightDevice('XF:19IDC-ES{MD2}:', name='front_light')
    aperature = MD2SimpleHVDevice('XF:19IDC-ES{MD2}:Aperature', name='aperature')
    scintillator = MD2SimpleHVDevice('XF:19IDC-ES{MD2}:Scintillator', name='scintillator')
    capillary = MD2SimpleHVDevice('XF:19IDC-ES{MD2}:Capillary', name='capillary')
    
    back_light = EpicsSignal(read_pv="XF:19IDD-CT{DIODE-Box_D1:4}InCh00:Data-RB",write_pv="XF:19IDD-CT{DIODE-Box_D1:4}OutCh00:Data-SP",name="back_light")
    back_light_low_limit = EpicsSignalRO("XF:19IDD-CT{DIODE-Box_D1:4}CfgCh00:LowLimit-RB",name="back_light_low_limit") 
    back_light_high_limit = EpicsSignalRO("XF:19IDD-CT{DIODE-Box_D1:4}CfgCh00:HighLimit-RB",name="back_light_high_limit")
    back_light_range = (back_light_low_limit.get(), back_light_high_limit.get())
    samplexyz = SampleXYZ("XF:19IDC-ES{Gon:1-Ax", name="samplexyz")
else:
    raise Exception(f"Invalid beamline name provided: {beamline}")

if beamline in ("amx", "fmx"):
    set_eiger_defaults(eiger)
