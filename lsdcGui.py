"""
The GUI for the LSDC system
"""
import sys
import os
import string
import math
import time
import urllib
import urllib.request
from io import BytesIO
from epics import PV
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import QtGui
from qtpy.QtCore import * 
from qtpy.QtGui import * 
QString = str
import db_lib
from qt_epics.QtEpicsMotorEntry import *
from qt_epics.QtEpicsMotorLabel import *
from qt_epics.QtEpicsPVLabel import *
from qt_epics.QtEpicsPVEntry import *
import cv2
from cv2 import *
from PIL import Image
from PIL import ImageQt
import daq_utils
from daq_utils import getBlConfig, setBlConfig
from config_params import *
import albulaUtils
import functools
from QPeriodicTable import *
from PyMca5.PyMcaGui.pymca.McaWindow import McaWindow, ScanWindow
from PyMca5.PyMcaGui.physics.xrf.McaAdvancedFit import McaAdvancedFit
from PyMca5.PyMcaPhysics.xrf import Elements
from element_info import element_info
import numpy as np
import _thread #TODO python document suggests using threading! make this chance once stable
import lsdcOlog
from threads import VideoThread, RaddoseThread
import socket
from utils.healthcheck import perform_checks

hostname = socket.gethostname()
ws_split = hostname.split('ws')
logging_file = 'lsdcGuiLog.txt'

import logging
import platform
from logging import handlers

class HostnameFilter(logging.Filter):
    hostname = platform.node().split('.')[0]

    def filter(self, record):
        record.hostname = HostnameFilter.hostname
        return True

logger = logging.getLogger()
logging.getLogger().setLevel(logging.INFO)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)
handler1 = handlers.RotatingFileHandler(logging_file, maxBytes=5000000, backupCount=100)
handler1.addFilter(HostnameFilter())
#handler2 = handlers.RotatingFileHandler('/var/log/dama/%slsdcGuiLog.txt' % os.environ['BEAMLINE_ID'], maxBytes=50000000)
#hostname added with help from: https://stackoverflow.com/questions/55584115/python-logging-how-to-track-hostname-in-logs
myformat = logging.Formatter('%(asctime)s %(hostname)s: %(name)-8s %(levelname)-8s %(message)s')
handler1.setFormatter(myformat)
#handler2.setFormatter(myformat)
logger.addHandler(handler1)
#logger.addHandler(handler2)
try:
  import ispybLib
except Exception as e:
  logger.error("lsdcGui: ISPYB import error, %s" % e)
import raddoseLib

global sampleNameDict
sampleNameDict = {}

global containerDict
containerDict = {}

def main():
    logger.info('Starting LSDC...')
    perform_checks()
    daq_utils.init_environment()
    daq_utils.readPVDesc()
    app = QtWidgets.QApplication(sys.argv)
    ex = ControlMain()
    sys.exit(app.exec_())

#skinner - I think Matt did a lot of what's below and I have no idea what it is. 
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f'Exception occured: {e}')    
