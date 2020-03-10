#!/opt/conda_envs/collection-2018-1.0/bin/ipython -i
"""
The server run when lsdcRemote is used
"""
import os
from daq_macros import *
import daq_lib
from daq_lib import *
from robot_lib import *
from beamline_lib import *
import atexit
from daq_main_common import pybass_init
import logging
from logging import handlers
logger = logging.getLogger()
logging.getLogger().setLevel(logging.INFO)
handler1 = handlers.RotatingFileHandler('lsdcServerLog.txt', maxBytes=50000000)
handler2 = handlers.RotatingFileHandler('/var/log/dama/%slsdcServerLog.txt' % os.environ['BEAMLINE_ID'], maxBytes=50000000)
myformat = logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s')
handler1.setFormatter(myformat)
handler2.setFormatter(myformat)
logger.addHandler(handler1)
logger.addHandler(handler2)

sitefilename = ""
global command_list,immediate_command_list,z
command_list = []
immediate_command_list = []
z = 25

pybass_init()

