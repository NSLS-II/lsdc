from start_bs import govs
from daq_lib import gui_message, toggleLowMagCameraSettings
import logging
logger = logging.getLogger(__name__)

gov_human = govs.gov.Human
gov_robot = govs.gov.Robot

def set_detz_in(distance):
    gov_human.dev.dz.target_In.set(distance)
    gov_robot.dev.dz.target_In.set(distance)

def set_detz_out(distance):
    gov_human.dev.dz.target_Out.set(distance)
    gov_robot.dev.dz.target_Out.set(distance)

def setGovRobot(state):
  try:
    logger.info(f"setGovRobot{state}")
    govStatus = gov_robot.set(state)
    waitGov(govStatus)
    if state in ["SA", "DA"]:
      toggleLowMagCameraSettings(state)
  except Exception: #TODO verify what kind of exception is thrown if we do not reach state
    logger.info(f"Governor did not reach {state}")

def waitGov(status):
  try:
    # TODO add callback for periodic updates
    failure = status.wait(GOVERNOR_TIMEOUT)
    return failure
  except StatusTimeoutError, WaitTimeoutError:
    message = 'Governor Timeout!'
    logger.error(message)
    gui_message(message)

