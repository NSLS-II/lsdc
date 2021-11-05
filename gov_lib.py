#from daq_lib import gui_message, toggleLowMagCameraSettings
from config_params import GOVERNOR_TIMEOUT
import logging
logger = logging.getLogger(__name__)

def set_detz_in(gov_robot, distance):
    gov_robot.dev.dz.target_In.set(distance)

def set_detz_out(gov_robot, distance):
    gov_robot.dev.dz.target_Out.set(distance)

def setGovRobot(gov_robot, state, wait=True):
  try:
    logger.info(f"setGovRobot{state}")
    govStatus = gov_robot.set(state)
    if wait:
      failure = waitGov(govStatus)
    else:
      failure = False
    if ((wait and not failure) or (not wait)) and (state in ["SA", "DA", "DI", "SE"]):
      pass #toggleLowMagCameraSettings(state)
    return {'failure': not failure, 'status': govStatus}
  except Exception: #TODO verify what kind of exception is thrown if we do not reach state
    logger.info(f"Governor did not reach {state}")
    return {'failure': 1, 'status': govStatus}

def waitGov(status, timeout=GOVERNOR_TIMEOUT):
  try:
    # TODO add callback for periodic updates
    failure = status.wait(timeout)
    return failure
  except (StatusTimeoutError, WaitTimeoutError) as e:
    message = 'Governor Timeout!'
    logger.error(message)
    #gui_message(message)

