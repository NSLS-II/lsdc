#!/opt/conda_envs/lsdc_dev3/bin/ipython -i
# import asyncio
from ophyd import *
from ophyd.mca import (Mercury1, SoftDXPTrigger)
from ophyd import Device, EpicsMotor, EpicsSignal, EpicsSignalRO
import os
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


class VectorProgramStart(Device):
    omega = Cpt(EpicsSignal, 'Pos:OStart-SP')
    x = Cpt(EpicsSignal, 'Pos:XStart-SP')
    y = Cpt(EpicsSignal, 'Pos:YStart-SP')
    z = Cpt(EpicsSignal, 'Pos:ZStart-SP')


class VectorProgramEnd(Device):
    omega = Cpt(EpicsSignal, 'Pos:OEnd-SP')
    x = Cpt(EpicsSignal, 'Pos:XEnd-SP')
    y = Cpt(EpicsSignal, 'Pos:YEnd-SP')
    z = Cpt(EpicsSignal, 'Pos:ZEnd-SP')


class VectorProgram(Device):
    start = Cpt(VectorProgramStart, '')
    end = Cpt(VectorProgramEnd, '')

    abort = Cpt(EpicsSignal, 'Cmd:Abort-Cmd', kind='omitted')
    go = Cpt(EpicsSignal, 'Cmd:Go-Cmd', kind='omitted')
    proceed = Cpt(EpicsSignal, 'Cmd:Proceed-Cmd', kind='omitted')
    sync = Cpt(EpicsSignal, 'Cmd:Sync-Cmd', kind='omitted')

    expose = Cpt(EpicsSignal, 'Expose-Sel')
    hold = Cpt(EpicsSignal, 'Hold-Sel')

    buffer_time = Cpt(EpicsSignal, 'Val:BufferTime-SP')
    frame_exptime = Cpt(EpicsSignal, 'Val:Exposure-SP')
    num_frames = Cpt(EpicsSignal, 'Val:NumSamples-SP')

    active = Cpt(EpicsSignalRO, 'Sts:Running-Sts')
    state = Cpt(EpicsSignalRO, 'Sts:State-Sts')


class StandardProsilica(SingleTrigger, ProsilicaDetector):
    image = Cpt(ImagePlugin, 'image1:')
    roi1 = Cpt(ROIPlugin, 'ROI1:')
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats5 = Cpt(StatsPlugin, 'Stats5:')


def filter_camera_data(camera):
    camera.read_attrs = ['stats1', 'stats5']
    camera.stats1.read_attrs = ['total', 'centroid']
    camera.stats5.read_attrs = ['total', 'centroid']


if (beamline=="amx"):
    mercury = ABBIXMercury('XF:17IDB-ES:AMX{Det:Mer}', name='mercury')
    mercury.read_attrs = ['mca.spectrum', 'mca.preset_live_time', 'mca.rois.roi0.count',
                                            'mca.rois.roi1.count', 'mca.rois.roi2.count', 'mca.rois.roi3.count']
    vdcm = VerticalDCM('XF:17IDA-OP:AMX{Mono:DCM', name='vdcm')
    vector_program = VectorProgram('XF:17IDB-ES:AMX{Gon:1-Vec}', name='vector_program')
else:
    mercury = ABBIXMercury('XF:17IDC-ES:FMX{Det:Mer}', name='mercury')
    mercury.read_attrs = ['mca.spectrum', 'mca.preset_live_time', 'mca.rois.roi0.count',
                                            'mca.rois.roi1.count', 'mca.rois.roi2.count', 'mca.rois.roi3.count']
    vdcm = VerticalDCM('XF:17IDA-OP:FMX{Mono:DCM', name='vdcm')
    vector_program = VectorProgram('XF:17IDC-ES:FMX{Gon:1-Vec}', name='vector_program')

