import daq_lib
from daq_utils import getBlConfig

class DensoRobot:
    def __init__(self, robot):
        self.robot = robot

    def preMount(self, puck_pos: int, pin_pos: int, samp_id: str):
        if getBlConfig('robot_online'):
            daq_lib.setGovRobot('SE')

    def mount(self, puck_pos: int, pin_pos: int, samp_id: str, **kwargs):
        try:
            self.robot.mount(get_puck_letter(puck_pos), str(pin_pos))
        except Exception as e:
            logger.error(f'Exception during mount step: {e}')
            return MOUNT_FAILURE
        return MOUNT_STEP_SUCCESSFUL

    def postMount(self, puck_pos: int, pin_pos: int, samp_id: str):
        if getBlConfig('robot_online'):
            daq_lib.setGovRobot('SA')

    def unmount(self, puck_pos: int, pin_pos: int, abs_pos=0):
        self.robot.dismount(str(puck_pos), str(pin_pos))
