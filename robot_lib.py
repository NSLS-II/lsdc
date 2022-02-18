import time
from beamline_support import getPvValFromDescriptor as getPvDesc, setPvValFromDescriptor as setPvDesc
import logging
from start_bs import robot, RE
from config_params import MOUNT_STEP_SUCCESSFUL, UNMOUNT_STEP_SUCCESSFUL, MOUNT_SUCCESSFUL, UNMOUNT_SUCCESSFUL
from denso_robot import DensoRobot
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

def mountRobotSample(gov_robot, puck_pos, pin_pos, samp_id, **kwargs):
  status, kwargs = robot.preMount(gov_robot, puck_pos, pin_pos, samp_id, **kwargs)  # TODO return governor status, send to mount function so embl robot can use it if necessary
  if status != MOUNT_STEP_SUCCESSFUL:
      return status
  RE(robot.mount(gov_robot, puck_pos, pin_pos, samp_id, **kwargs))
  if isinstance(robot, DensoRobot):
    status = robot.check_sample_mounted(mount=True, puck_pos=puck_pos, pin_pos=pin_pos)
  else:
    status = MOUNT_STEP_SUCCESSFUL  # TODO assume embl robot is successful
  if status != MOUNT_STEP_SUCCESSFUL:
      return status
  status = robot.postMount(gov_robot, puck_pos, pin_pos, samp_id)
  return MOUNT_SUCCESSFUL  # TODO hard-coded for testing

def unmountRobotSample(gov_robot, puck_pos, pin_pos, samp_id):
  status = robot.preUnmount(gov_robot, puck_pos, pin_pos, samp_id)
  if status != UNMOUNT_STEP_SUCCESSFUL:
      return status
  RE(robot.unmount(gov_robot, puck_pos, pin_pos, samp_id))
  if isinstance(robot, DensoRobot):
    status = robot.check_sample_mounted(mount=False, puck_pos=puck_pos, pin_pos=pin_pos)
  else:
    status = UNMOUNT_STEP_SUCCESSFUL  # TODO assume embl robot is successful
  return UNMOUNT_SUCCESSFUL  # TODO hard-coded for testing

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
