import daq_lib
from daq_utils import getBlConfig
from config_params import MOUNT_SUCCESSFUL, MOUNT_STEP_SUCCESSFUL, MOUNT_FAILURE,\
                          UNMOUNT_SUCCESSFUL, UNMOUNT_FAILURE
import gov_lib
import logging
logger = logging.getLogger(__name__)

def get_puck_letter(puck_number):
    return chr(ord('@') + int(puck_number))

class DensoRobot:
    def __init__(self, robot):
        self.robot = robot

    def preMount(self, gov_robot, puck_pos: int, pin_pos: int, samp_id: str, **kwargs):
        if getBlConfig('robot_online'):
            try:
                status = gov_lib.setGovRobot(gov_robot, 'SE')
                kwargs['govStatus'] = status
            except Exception as e:
                logger.error(f'Exception while in preMount step: {e}')
                return MOUNT_FAILURE
        return MOUNT_STEP_SUCCESSFUL, kwargs

    def mount(self, gov_robot, puck_pos: int, pin_pos: int, samp_id: str, **kwargs):
        try:
            logger.info(f'Mounting: {puck_pos} {pin_pos}')
            yield from self.robot.mount(get_puck_letter(puck_pos), str(pin_pos))
        except Exception as e:
            logger.error(f'Exception during mount step: {e}')
            return MOUNT_FAILURE
        return MOUNT_STEP_SUCCESSFUL

    def postMount(self, gov_robot, puck_pos: int, pin_pos: int, samp_id: str, **kwargs):
        if getBlConfig('robot_online'):
            try:
                gov_lib.setGovRobot(gov_robot, 'SA')
            except Exception as e:
                logger.error(f'Exception while in postMount step: {e}')
                return MOUNT_FAILURE
        return MOUNT_SUCCESSFUL

    def preUnmount(self, gov_robot, puck_pos: int, pin_pos: int, samp_id: str):
        if getBlConfig('robot_online'):
            logger.info(f"unmounting {puck_pos} {pin_pos} {samp_id}")
            try:
                daq_lib.setRobotGovState(gov_robot, "SE")
            except Exception as e:
                logger.error('Exception while in preUnmount step: {e}')
                return UNMOUNT_FAILURE
        return UNMOUNT_STEP_SUCCESSFUL

    def unmount(self, gov_robot, puck_pos: int, pin_pos: int, samp_id: str):
        try:
            logger.info(f'dismount {puck_pos} {pin_pos}')
            yield from self.robot.dismount(get_puck_letter(puck_pos), str(pin_pos))
        except Exception as e:
            logger.error(f'Exception while unmounting sample: {e}')
            return UNMOUNT_FAILURE
        return UNMOUNT_SUCCESSFUL

    def finish(self):
        ...
