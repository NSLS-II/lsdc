from daq_utils import getBlConfig
import daq_lib
import time
import daq_macros
from beamline_support import getPvValFromDescriptor as getPvDesc, setPvValFromDescriptor as setPvDesc
import logging

from config_params import MOUNT_SUCCESSFUL, MOUNT_FAILURE, MOUNT_UNRECOVERABLE_ERROR
logger = logging.getLogger(__name__)

global method_pv,var_pv,pinsPerPuck
pinsPerPuck = 16

global sampXadjust, sampYadjust, sampZadjust
sampXadjust = 0
sampYadjust = 0
sampZadjust = 0

global retryMountCount
retryMountCount = 0

def setWorkposThread(init,junk):
  logger.info("setting work pos in thread")
  setPvDesc("robotGovActive",1)
  setPvDesc("robotXWorkPos",getPvDesc("robotXMountPos"))
  setPvDesc("robotYWorkPos",getPvDesc("robotYMountPos"))
  setPvDesc("robotZWorkPos",getPvDesc("robotZMountPos"))
  setPvDesc("robotOmegaWorkPos",90.0)
  if (init):
    time.sleep(20)
    setPvDesc("robotGovActive",0)

def mountRobotSample(puck_pos, pin_pos, samp_id, **kwargs):
  global retryMountCount
  status, kwargs = robot.preMount(puck_pos, pin_pos, samp_id, kwargs)
  if status:
      return status
  try:
    status = robot.mount(puck_pos, pin_pos, samp_id, kwargs)
    if status:
        return status
  except Exception as e:
    # note: much of this code is based on topview results
    # TODO organize better? extract to embl_robot?
    logger.error(e)
    e_s = str(e)
    if (e_s.find("Fatal") != -1):
      daq_macros.robotOff()
      daq_macros.disableMount()
      daq_lib.gui_message(e_s + ". FATAL ROBOT ERROR - CALL STAFF! robotOff() executed.")
      return MOUNT_FAILURE
    if (e_s.find("tilted") != -1 or e_s.find("Load Sample Failed") != -1):
      if (getBlConfig("queueCollect") == 0):
        daq_lib.gui_message(e_s + ". Try mounting again")
        return MOUNT_FAILURE
      else:
        if (retryMountCount == 0):
          retryMountCount+=1
          mountStat = robot.mount(puck_pos,pin_pos,samp_id, kwargs)
          if (mountStat == MOUNT_SUCCESSFUL):
            retryMountCount = 0
          return mountStat
        else:
          retryMountCount = 0
          daq_lib.gui_message("ROBOT: Could not recover from " + e_s)
          return MOUNT_UNRECOVERABLE_ERROR
    daq_lib.gui_message("ROBOT mount ERROR: " + e_s)
    return MOUNT_FAILURE

  status = robot.postMount(puck_pos, pin_pos, samp_id)
  return status

def unmountRobotSample(puck_pos, pin_pos, samp_id):
  robot.preUnmount(puck_pos, pin_pos, samp_id)
  robot.unmount(puck_pos, pin_pos, samp_id)
  return MOUNT_SUCCESSFUL
