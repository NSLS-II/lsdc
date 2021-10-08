from start_bs import govs
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
