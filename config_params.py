from enum import Enum

# BlConfig parameters

# rastering parameters
RASTER_TUNE_LOW_RES = 'rasterTuneLowRes'
RASTER_TUNE_HIGH_RES = 'rasterTuneHighRes'
RASTER_TUNE_ICE_RING_FLAG = 'rasterTuneIceRingFlag'
RASTER_TUNE_RESO_FLAG = 'rasterTuneResoFlag'
RASTER_TUNE_ICE_RING_WIDTH = 'rasterTuneIceRingWidth'
RASTER_DOZOR_SPOT_LEVEL = 'rasterDozorSpotLevel'
RASTER_NUM_CELLS_DELAY_THRESHOLD = 'rasterNumCellsThresholdDelay'

# timing delays
ISPYB_RESULT_ENTRY_DELAY = 'ispybResultEntryDelay'
RASTER_LONG_SNAPSHOT_DELAY = 'rasterLongSnapshotDelay'
RASTER_SHORT_SNAPSHOT_DELAY = 'rasterShortSnapshotDelay'
RASTER_POST_SNAPSHOT_DELAY = 'rasterPostSnapshotDelay'
RASTER_GUI_XREC_FILL_DELAY = 'rasterGuiXrecFillDelay'

# governor transition gain/exposure times
LOW_MAG_GAIN_DA = 'lowMagGainDA'
LOW_MAG_GAIN = 'lowMagGain'
LOW_MAG_EXP_TIME_DA = 'lowMagExptimeDA'
LOW_MAG_EXP_TIME = 'lowMagExptime'

# top view
TOP_VIEW_CHECK = 'topViewCheck'

# raster request status updates
class RasterStatus(Enum):
    """The lsdc server can keep GUI clients updated on the status of
    of raster macros by updating raster request objects in the request
    database. The GUI can process raster data, e.g. filling heat maps,
    in parallel to the server moving motors and adjusting low mag cam.
    """
    NEW = 0
    DRAWN = 1
    READY_FOR_FILL = 2
    READY_FOR_SNAPSHOT = 3
    READY_FOR_REPROCESS = 4

HUTCH_TIMER_DELAY = 1000
SAMPLE_TIMER_DELAY = 0

ROBOT_MIN_DISTANCE = 200.0
ROBOT_DISTANCE_TOLERANCE = 0.050

FAST_DP_MIN_NODES = 4
SPOT_MIN_NODES = 8
