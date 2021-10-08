from start_bs import govs
from daq_lib import gui_message, toggleLowMagCameraSettings
from config_params import GOVERNOR_TIMEOUT
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

def setGovRobot(state, wait=True):
  try:
    logger.info(f"setGovRobot{state}")
    govStatus = gov_robot.set(state)
    if wait:
      failure = waitGov(govStatus)
    else:
      failure = False
    if ((wait and not failure) or (not wait)) and (state in ["SA", "DA", "DI", "SE"]):
      toggleLowMagCameraSettings(state)
    return {'failure': not failure, 'status': govStatus}
  except Exception: #TODO verify what kind of exception is thrown if we do not reach state
    logger.info(f"Governor did not reach {state}")
    return {'failure': 1, 'status': govStatus}

def waitGov(status, timeout=GOVERNOR_TIMEOUT):
  try:
    # TODO add callback for periodic updates
    failure = status.wait(timeout)
    return failure
  except StatusTimeoutError, WaitTimeoutError:
    message = 'Governor Timeout!'
    logger.error(message)
    gui_message(message)

