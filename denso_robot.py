from daq_utils import getBlConfig
from config_params import MOUNT_SUCCESSFUL, MOUNT_STEP_SUCCESSFUL, MOUNT_FAILURE,\
                          UNMOUNT_SUCCESSFUL, UNMOUNT_STEP_SUCCESSFUL, UNMOUNT_FAILURE
import gov_lib
import traceback
import logging
logger = logging.getLogger(__name__)

def get_denso_puck_pin(puck_number, pin_number):
    return (chr(ord('@') + int(puck_number)), str(pin_number + 1))  # input value is zero-indexed, Denso pin is one-indexed

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
            denso_puck_pos, denso_pin_pos = get_denso_puck_pin(puck_pos, pin_pos)
            logger.info(f'Mounting: {denso_puck_pos} {denso_pin_pos}')
            yield from self.robot.mount(denso_puck_pos, denso_pin_pos)
        except Exception as e:
            logger.error(f'Exception during mount step: {e}: traceback: {traceback.format_exc()}')
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
            denso_puck_pos, denso_pin_pos = get_denso_puck_pin(puck_pos, pin_pos)
            logger.info(f"preparing to unmount {denso_puck_pos} {denso_pin_pos} {samp_id}")
            try:
                gov_lib.setGovRobot(gov_robot, "SE")
            except Exception as e:
                logger.error(f'Exception while in preUnmount step: {e}')
                return UNMOUNT_FAILURE
        return UNMOUNT_STEP_SUCCESSFUL

    def unmount(self, gov_robot, puck_pos: int, pin_pos: int, samp_id: str):
        denso_puck_pos, denso_pin_pos = get_denso_puck_pin(puck_pos, pin_pos)
        try:
            logger.info(f'dismount {denso_puck_pos} {denso_pin_pos}')
            yield from self.robot.dismount(denso_puck_pos, denso_pin_pos)
        except Exception as e:
            logger.error(f'Exception while unmounting sample: {e}')
            return UNMOUNT_FAILURE
        return UNMOUNT_SUCCESSFUL

    def finish(self):
        ...

    def check_sample_mounted(self, mount, puck_pos, pin_pos):  # is the correct sample present/absent as expected during a mount/unmount?
        if mount:
            check_occupied = 1
        else:
            check_occupied = 0
        if int(self.robot.spindle_occupied_sts.get()) == check_occupied and \
           int(self.robot.puck_num_sel.get()) == puck_pos - 1 and \
           int(self.robot.sample_num_sel.get()) == pin_pos:
            if mount:
                return MOUNT_SUCCESSFUL
            else:
                return UNMOUNT_SUCCESSFUL
        else:
            if mount:
                return MOUNT_FAILURE
            else:
                return UNMOUNT_FAILURE
