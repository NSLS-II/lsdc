#!/opt/conda_envs/collection-2018-1.0/bin/ipython -i
"""
The main server for the LSDC system
"""
import string
import sys
import os
import time
import _thread
import atexit
from daq_main_common import pybass_init, run_server

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

def main(mode):
  pybass_init()
  if (mode=="gui"):
    run_server()
  else:
    lsdcHome = os.environ["LSDCHOME"]
    os.system(lsdcHome+"/daq_main2.py gui&")    

if (len(sys.argv)>1):
  if (sys.argv[1] == "gui"):
    main(mode="gui")
else:
  main(mode="shell")  
