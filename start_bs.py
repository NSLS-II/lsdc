#!/opt/conda_envs/lsdc_dev3/bin/ipython -i
# import asyncio
from ophyd import *
from ophyd.mca import (Mercury1, SoftDXPTrigger)
from ophyd import Device, EpicsMotor, EpicsSignal, EpicsSignalRO
from mxtools.zebra import Zebra
from mxtools.vector_program import VectorProgram
from mxtools.eiger import EigerSingleTriggerV26, set_eiger_defaults
import os
from mxtools.governor import _make_governors

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

# import nslsii

# Register bluesky IPython magics.
#from bluesky.magics import BlueskyMagics
#get_ipython().register_magics(BlueskyMagics)

#nslsii.configure_base(get_ipython().user_ns, 'amx')
import bluesky.plans as bp

from bluesky.run_engine import RunEngine
from bluesky.utils import get_history, PersistentDict
RE = RunEngine()
beamline = os.environ["BEAMLINE_ID"]
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
    x = Cpt(EpicsMotor, ':GX}Mtr')
    y = Cpt(EpicsMotor, ':PY}Mtr')
    z = Cpt(EpicsMotor, ':PZ}Mtr')
    omega = Cpt(EpicsMotor, ':O}Mtr')

if (beamline=="amx"):
    mercury = ABBIXMercury('XF:17IDB-ES:AMX{Det:Mer}', name='mercury')
    mercury.read_attrs = ['mca.spectrum', 'mca.preset_live_time', 'mca.rois.roi0.count',
                                            'mca.rois.roi1.count', 'mca.rois.roi2.count', 'mca.rois.roi3.count']
    vdcm = VerticalDCM('XF:17IDA-OP:AMX{Mono:DCM', name='vdcm')
    zebra = Zebra('XF:17IDB-ES:AMX{Zeb:2}:', name='zebra')
    eiger = EigerSingleTriggerV26('XF:17IDB-ES:AMX{Det:Eig9M}', name='eiger', beamline=beamline)
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

elif beamline == "fmx":  
    mercury = ABBIXMercury('XF:17IDC-ES:FMX{Det:Mer}', name='mercury')
    mercury.read_attrs = ['mca.spectrum', 'mca.preset_live_time', 'mca.rois.roi0.count',
                                            'mca.rois.roi1.count', 'mca.rois.roi2.count', 'mca.rois.roi3.count']
    vdcm = VerticalDCM('XF:17IDA-OP:FMX{Mono:DCM', name='vdcm')
    zebra = Zebra('XF:17IDC-ES:FMX{Zeb:3}:', name='zebra')
    eiger = EigerSingleTriggerV26('XF:17IDC-ES:FMX{Det:Eig16M}', name='eiger', beamline=beamline)
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

elif beamline=="nyx":
    mercury = ABBIXMercury('XF:17IDC-ES:FMX{Det:Mer}', name='mercury')
    mercury.read_attrs = ['mca.spectrum', 'mca.preset_live_time', 'mca.rois.roi0.count',
                                            'mca.rois.roi1.count', 'mca.rois.roi2.count', 'mca.rois.roi3.count']
    vdcm = VerticalDCM('XF:17IDA-OP:FMX{Mono:DCM', name='vdcm')
    zebra = Zebra('XF:19IDC-ES{Zeb:1}:', name='zebra')
    vector = VectorProgram("XF:19IDC-ES{Gon:1-Vec}", name="vector")
    from mxtools.eiger import EigerSingleTriggerV26
    detector = EigerSingleTriggerV26("XF:19ID-ES:NYX{Det:Eig9M}", name="detector", beamline=beamline)
    from nyxtools.flyer_eiger2 import NYXEiger2Flyer
    flyer = NYXEiger2Flyer(vector, zebra, detector)
    from mxtools.raster_flyer import MXRasterFlyer
    raster_flyer = MXRasterFlyer(vector, zebra, eiger)

    from nyxtools.robot import DensoOphydRobot
    from denso_robot import DensoRobot
    denso_ophyd_robot = DensoOphydRobot("XF:19IDC-ES{Rbt:1}", name="robot")
    robot = DensoRobot(denso_ophyd_robot) # DensoRobot is the robot_lib API-compatible object
    govs = _make_governors("XF:19IDC-ES", name="govs")
    gov_robot = govs.gov.Robot

    back_light = EpicsSignal(read_pv="XF:19IDD-CT{DIODE-Box_D1:4}InCh00:Data-RB",write_pv="XF:19IDD-CT{DIODE-Box_D1:4}OutCh00:Data-SP",name="back_light")
    back_light_low_limit = EpicsSignalRO("XF:19IDD-CT{DIODE-Box_D1:4}CfgCh00:LowLimit-RB",name="back_light_low_limit") 
    back_light_high_limit = EpicsSignalRO("XF:19IDD-CT{DIODE-Box_D1:4}CfgCh00:HighLimit-RB",name="back_light_high_limit")
    back_light_range = (back_light_low_limit.get(), back_light_high_limit.get())
else:
    raise Exception(f"Invalid beamline name provided: {beamline}")

if beamline in ("amx", "fmx"):
    set_eiger_defaults(eiger)
