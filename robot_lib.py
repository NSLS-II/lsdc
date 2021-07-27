import time
from beamline_support import getPvValFromDescriptor as getPvDesc, setPvValFromDescriptor as setPvDesc
import logging

from config_params import MOUNT_SUCCESSFUL
logger = logging.getLogger(__name__)

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
  status, kwargs = robot.preMount(puck_pos, pin_pos, samp_id, kwargs)
  if status:
      return status
  status = robot.mount(puck_pos, pin_pos, samp_id, kwargs)
  if status:
      return status
  status = robot.postMount(puck_pos, pin_pos, samp_id)
  return status

def unmountRobotSample(puck_pos, pin_pos, samp_id):
  robot.preUnmount(puck_pos, pin_pos, samp_id)
  robot.unmount(puck_pos, pin_pos, samp_id)
  return MOUNT_SUCCESSFUL

def finish():
    robot.finish()

def recoverRobot():
    robot.recoverRobot()

def dryGripper():
    robot.dryGripper()

# TODO ask Edwin about these Dewar functions
def DewarAutoFillOn():
    robot.DewarAutoFillOn()

def DewarAutoFillOff():
    robot.DewarAutoFillOff()

def DewarHeaterOn():
    robot.DewarHeaterOn()

def DewarHeaterOff():
    robot.DewarHeaterOff()

def warmupGripper():
    robot.warmupGripper()

def enableDewarTscreen():
    robot.enableDewarTscreen()

def openPort(portNo):
    robot.openPort(portNo)

def closePorts():
    robot.closePorts()

def rebootEMBL():
    robot.rebootEMBL()

def parkGripper():
    robot.parkGripper()

def testRobot():
    robot.testRobot()

def openGripper():
    robot.openGripper()

def closeGripper():
    robot.closeGripper()
