#from daq_lib import gui_message, toggleLowMagCameraSettings
from config_params import GOVERNOR_TIMEOUT
from ophyd.utils.errors import StatusTimeoutError, WaitTimeoutError
import ophyd
from ophyd import StatusBase
import logging
logger = logging.getLogger(__name__)

def set_detz_in(gov_robot, distance):
    gov_robot.dev.dz.target_Work.set(distance)

def set_detz_out(gov_robot, distance):
    gov_robot.dev.dz.target_Safe.set(distance)

def setGovRobot(gov_robot, state, wait=True):
  try:
    logger.info(f"setGovRobot{state}")
    govStatus = gov_robot.set(state)
    if wait:
      waitGov(govStatus)
    if wait and govStatus.success and gov_robot.state.get() != state:
      raise Exception(f'Did not reach expected state "{state}". actual state is "{gov_robot.state.get()}"')
    if ((wait and govStatus.success) or not wait) and state in ["SA", "DA", "DI", "SE"]:
      pass #toggleLowMagCameraSettings(state)
    return govStatus
  except Exception as e:
    logger.info(f"Governor did not reach {state}")
    govStatus = StatusBase()
    govStatus.set_exception(e)
    return govStatus

def waitGov(status, timeout=GOVERNOR_TIMEOUT):
  try:
    # TODO add callback for periodic updates
    ophyd.status.wait(status, timeout)
  except (StatusTimeoutError, WaitTimeoutError) as e:
    message = 'Governor Timeout!'
    logger.error(message)
    #gui_message(message)

def waitGovNoSleep(timeout=GOVERNOR_TIMEOUT):
  pass
