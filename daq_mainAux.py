#!/opt/conda_envs/collection-2018-1.0/bin/ipython -i
"""
The server run when lsdcRemote is used
"""
import string
import sys
import os
import time
import _thread
import db_lib
import daq_macros
from daq_macros import *
import daq_lib
from daq_lib import *
import daq_utils
from robot_lib import *
import det_lib
import beamline_support
import beamline_lib
from beamline_lib import *
import atexit
from daq_main_common import pybass_init
import logging
logger = logging.getLogger(__name__)

sitefilename = ""
global command_list,immediate_command_list,z
command_list = []
immediate_command_list = []
z = 25

pybass_init()

