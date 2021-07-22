import RobotControlLib
import daq_utils
import db_lib
from daq_utils import getBlConfig
import daq_lib
import beamline_lib
import time
import daq_macros
import beamline_support
from beamline_support import getPvValFromDescriptor as getPvDesc, setPvValFromDescriptor as setPvDesc
import os
import sys
import traceback
import filecmp
import _thread
import logging
import epics.ca
import top_view

from config_params import TOP_VIEW_CHECK, MOUNT_SUCCESSFUL, MOUNT_FAILURE
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

def mountRobotSample():
  global retryMountCount
  try:
    robot.preMountRobotSample()
    robot.mountRobotSample()
    robot.postMountRobotSample()
    if (getBlConfig(TOP_VIEW_CHECK) == 1):
      daq_lib.setGovRobot('SA')  #make sure we're in SA before moving motors
      if (sampYadjust != 0):
        pass
      else:
        logger.info("Cannot align pin - Mount next sample.")
#else it thinks it worked            return 0

      daq_lib.setGovRobot('SA')
      return MOUNT_SUCCESSFUL
  except Exception as e:
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
          mountStat = mountRobotSample(puckPos,pinPos,sampID,init)
          if (mountStat == MOUNT_SUCCESSFUL):
            retryMountCount = 0
          return mountStat
        else:
          retryMountCount = 0
          daq_lib.gui_message("ROBOT: Could not recover from " + e_s)
          return MOUNT_UNRECOVERABLE_ERROR
    daq_lib.gui_message("ROBOT mount ERROR: " + e_s)
    return MOUNT_FAILURE
  return MOUNT_SUCCESSFUL

def unmount():
  robot.preUnmount()
  robot.unmount()
  return MOUNT_SUCCESSFUL
