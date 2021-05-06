"""
The GUI for the LSDC system
"""
import sys
import os
import string
import math
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

import socket
hostname = socket.gethostname()
ws_split = hostname.split('ws')
if len(ws_split) == 2 and ws_split[1] == '1': #ws1 staff local
    logging_file = 'lsdcGuiLog.txt'
elif len(ws_split) == 2 and ws_split[1] == '3': #ws3 user remote
    user = os.environ['USER']
    logging_file = '/nsls2/users/%s/lsdcGuiLog.txt' % user
    print('LSDC GUI log file is in the home directory %s' % logging_file)
else:
    print('lsdcGui not being run on one of the "normal" workstations. log going into home directory of current user')
    user = os.environ['USER']
    logging_file = '/nsls2/users/%s/lsdcGuiLog.txt' % user
import logging
from logging import handlers
logger = logging.getLogger()
logging.getLogger().setLevel(logging.INFO)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)
handler1 = handlers.RotatingFileHandler(logging_file, maxBytes=5000000, backupCount=100)
#TODO find a place to put GUI log files - must work remotely and locally, ideally the same place for all instances
#handler2 = handlers.RotatingFileHandler('/var/log/dama/%slsdcGuiLog.txt' % os.environ['BEAMLINE_ID'], maxBytes=50000000)
myformat = logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s')
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

cryostreamTempPV = {'amx': 'AMX:cs700:gasT-I', 'fmx': 'FMX:cs700:gasT-I'}

HUTCH_TIMER_DELAY = 1000

VALID_EXP_TIMES = {'amx':{'min':0.005, 'max':1, 'digits':3}, 'fmx':{'min':0.01, 'max':10, 'digits':3}}
VALID_DET_DIST = {'amx':{'min': 100, 'max':500, 'digits':3}, 'fmx':{'min':137, 'max':2000, 'digits':2}}
VALID_TOTAL_EXP_TIMES = {'amx':{'min':0.005, 'max':300, 'digits':3}, 'fmx':{'min':0.01, 'max':300, 'digits':3}}
VALID_PREFIX_LENGTH = 25 #TODO centralize with spreadsheet validation?
VALID_PREFIX_NAME = '[0-9a-zA-Z-_]{0,%s}' % VALID_PREFIX_LENGTH

class SnapCommentDialog(QtWidgets.QDialog):
    def __init__(self,parent = None):
        QtWidgets.QDialog.__init__(self,parent)
        self.setWindowTitle("Snapshot Comment")
        self.setModal(False)
        vBoxColParams1 = QtWidgets.QVBoxLayout()
        hBoxColParams1 = QtWidgets.QHBoxLayout()
        self.textEdit = QtWidgets.QPlainTextEdit()
        vBoxColParams1.addWidget(self.textEdit)
        self.ologCheckBox = QCheckBox("Save to Olog")
        self.ologCheckBox.setChecked(False)
        vBoxColParams1.addWidget(self.ologCheckBox)        
        commentButton = QtWidgets.QPushButton("Add Comment")        
        commentButton.clicked.connect(self.commentCB)
        cancelButton = QtWidgets.QPushButton("Cancel")        
        cancelButton.clicked.connect(self.cancelCB)
        
        hBoxColParams1.addWidget(commentButton)
        hBoxColParams1.addWidget(cancelButton)
        vBoxColParams1.addLayout(hBoxColParams1)
        self.setLayout(vBoxColParams1)

      
    def cancelCB(self):
      self.comment = ""
      self.useOlog = False
      self.reject()

    def commentCB(self):
      self.comment = self.textEdit.toPlainText()
      self.useOlog = self.ologCheckBox.isChecked()
      self.accept()
    
    @staticmethod
    def getComment(parent = None):
        dialog = SnapCommentDialog(parent)
        result = dialog.exec_()
        return (dialog.comment, dialog.useOlog,result == QDialog.Accepted)

class RasterExploreDialog(QtWidgets.QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setModal(False)
        self.setWindowTitle("Raster Explore")
        vBoxParams1 = QtWidgets.QVBoxLayout()
        hBoxParams1 = QtWidgets.QHBoxLayout()
        hBoxParams2 = QtWidgets.QHBoxLayout()
        hBoxParams3 = QtWidgets.QHBoxLayout()
        spotCountLabel = QtWidgets.QLabel('Spot Count:')
        spotCountLabel.setFixedWidth(120)
        self.spotCount_ledit = QtWidgets.QLabel()
        self.spotCount_ledit.setFixedWidth(60)
        hBoxParams1.addWidget(spotCountLabel)
        hBoxParams1.addWidget(self.spotCount_ledit)
        intensityLabel = QtWidgets.QLabel('Total Intensity:')
        intensityLabel.setFixedWidth(120)
        self.intensity_ledit = QtWidgets.QLabel()
        self.intensity_ledit.setFixedWidth(60)
        hBoxParams2.addWidget(intensityLabel)
        hBoxParams2.addWidget(self.intensity_ledit)
        resoLabel = QtWidgets.QLabel('Resolution:')
        resoLabel.setFixedWidth(120)
        self.reso_ledit = QtWidgets.QLabel()
        self.reso_ledit.setFixedWidth(60)
        hBoxParams3.addWidget(resoLabel)
        hBoxParams3.addWidget(self.reso_ledit)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.buttons()[0].clicked.connect(self.rasterExploreCancelCB)
        vBoxParams1.addLayout(hBoxParams1)
        vBoxParams1.addLayout(hBoxParams2)
        vBoxParams1.addLayout(hBoxParams3)
        vBoxParams1.addWidget(self.buttons)
        self.setLayout(vBoxParams1)


    def setSpotCount(self,val):
      self.spotCount_ledit.setText(str(val))

    def setTotalIntensity(self,val):
      self.intensity_ledit.setText(str(val))

    def setResolution(self,val):
      self.reso_ledit.setText(str(val))

    def rasterExploreCancelCB(self):
      self.done(QDialog.Rejected)


class StaffScreenDialog(QFrame):  
    def __init__(self,parent = None):
        self.parent=parent
        QFrame.__init__(self)
        self.setWindowTitle("Staff Only")
        self.spotNodeCount = 8
        self.fastDPNodeCount = 4
        self.cpuCount = 28
        vBoxColParams1 = QtWidgets.QVBoxLayout()
        hBoxColParams0 = QtWidgets.QHBoxLayout()                
        hBoxColParams1 = QtWidgets.QHBoxLayout()        
        hBoxColParams2 = QtWidgets.QHBoxLayout()
        hBoxColParams3 = QtWidgets.QHBoxLayout()
        hBoxFastDP = QtWidgets.QHBoxLayout()
        hBoxSpotfinder = QtWidgets.QHBoxLayout()
        puckToDewarButton = QtWidgets.QPushButton("Puck to Dewar...")
        puckToDewarButton.clicked.connect(self.parent.puckToDewarCB)
        removePuckButton = QtWidgets.QPushButton("Remove Puck...")
        removePuckButton.clicked.connect(self.parent.removePuckCB)
        hBoxColParams0.addWidget(puckToDewarButton)
        hBoxColParams0.addWidget(removePuckButton )                        
        self.robotOnCheckBox = QCheckBox("Robot (On)")
        if (getBlConfig("robot_online") == 1):
          self.robotOnCheckBox.setChecked(True)
        else:
          self.robotOnCheckBox.setChecked(False)            
        self.robotOnCheckBox.stateChanged.connect(self.robotOnCheckCB)
        self.topViewCheckOnCheckBox = QCheckBox("TopViewCheck (On)")
        if (getBlConfig(TOP_VIEW_CHECK) == 1):
          self.topViewCheckOnCheckBox.setChecked(True)
        else:
          self.topViewCheckOnCheckBox.setChecked(False)            
        self.topViewCheckOnCheckBox.stateChanged.connect(self.topViewOnCheckCB)
        self.queueCollectOnCheckBox = QCheckBox("Queue Collect")
        hBoxColParams1.addWidget(self.queueCollectOnCheckBox)
        if (getBlConfig("queueCollect") == 1):
          self.queueCollectOnCheckBox.setChecked(True)
        else:
          self.queueCollectOnCheckBox.setChecked(False)            
        self.queueCollectOnCheckBox.stateChanged.connect(self.queueCollectOnCheckCB)
        self.vertRasterOnCheckBox = QCheckBox("Vert. Raster")
        hBoxColParams1.addWidget(self.vertRasterOnCheckBox)        
        if (getBlConfig("vertRasterOn") == 1):
          self.vertRasterOnCheckBox.setChecked(True)
        else:
          self.vertRasterOnCheckBox.setChecked(False)            
        self.vertRasterOnCheckBox.stateChanged.connect(self.vertRasterOnCheckCB)
        self.procRasterOnCheckBox = QCheckBox("Process Raster")
        hBoxColParams1.addWidget(self.procRasterOnCheckBox)        
        if (getBlConfig("rasterProcessFlag") == 1):
          self.procRasterOnCheckBox.setChecked(True)
        else:
          self.procRasterOnCheckBox.setChecked(False)            
        self.procRasterOnCheckBox.stateChanged.connect(self.procRasterOnCheckCB)
        self.guiRemoteOnCheckBox = QCheckBox("GUI Remote")
        hBoxColParams1.addWidget(self.guiRemoteOnCheckBox)        
        if (getBlConfig("omegaMonitorPV") == "VAL"):
          self.guiRemoteOnCheckBox.setChecked(True)
        else:
          self.guiRemoteOnCheckBox.setChecked(False)            
        self.guiRemoteOnCheckBox.stateChanged.connect(self.guiRemoteOnCheckCB)
        self.enableMountCheckBox = QCheckBox("Enable Mount")
        if (getBlConfig("mountEnabled") == 1):
          self.enableMountCheckBox.setChecked(True)
        else:
          self.enableMountCheckBox.setChecked(False)            
        self.enableMountCheckBox.stateChanged.connect(self.enableMountCheckCB)
        self.unmountColdButton = QtWidgets.QPushButton("Unmount Cold")
        self.unmountColdButton.clicked.connect(self.unmountColdCB)
        self.openPort1Button = QtWidgets.QPushButton("Open Port 1")
        self.openPort1Button.clicked.connect(self.openPort1CB)
        self.closePortsButton = QtWidgets.QPushButton("Close Ports")
        self.closePortsButton.clicked.connect(self.closePortsCB)
        self.warmupButton = QtWidgets.QPushButton("Dry Gripper")        
        self.warmupButton.clicked.connect(self.parent.dryGripperCB)
        self.enableTScreenButton = QtWidgets.QPushButton("Enable Dewar Tscreen")        
        self.enableTScreenButton.clicked.connect(self.parent.enableTScreenGripperCB)
        self.parkButton = QtWidgets.QPushButton("Park Gripper")        
        self.parkButton.clicked.connect(self.parent.parkGripperCB)
        self.homePinsButton = QtWidgets.QPushButton("Home Pins")
        self.homePinsButton.clicked.connect(self.homePinsCB)
        self.clearMountedSampleButton = QtWidgets.QPushButton("Clear Mounted Sample")
        self.clearMountedSampleButton.clicked.connect(self.clearMountedSampleCB)
        hBoxColParams2.addWidget(self.openPort1Button)
        hBoxColParams2.addWidget(self.closePortsButton)        
        hBoxColParams2.addWidget(self.unmountColdButton)
        hBoxColParams2.addWidget(self.warmupButton)
        hBoxColParams2.addWidget(self.enableTScreenButton)
        hBoxColParams2.addWidget(self.parkButton)                        
        hBoxColParams2.addWidget(self.clearMountedSampleButton)
        hBoxColParams1.addWidget(self.homePinsButton)        
        self.setFastDPNodesButton = QtWidgets.QPushButton("Set FastDP Nodes")
        self.setFastDPNodesButton.clicked.connect(self.setFastDPNodesCB)
        hBoxFastDP.addWidget(self.setFastDPNodesButton)        
        self.fastDPNodeEntryList = []
        nodeList = self.getFastDPNodeList()        
        for i in range (0,self.fastDPNodeCount):
          self.fastDPNodeEntryList.append(QtWidgets.QLineEdit())
          self.fastDPNodeEntryList[i].setFixedWidth(30)
          self.fastDPNodeEntryList[i].setText(str(nodeList[i]))
          hBoxFastDP.addWidget(self.fastDPNodeEntryList[i])
        self.setBeamcenterButton = QtWidgets.QPushButton("Set Beamcenter")
        self.setBeamcenterButton.clicked.connect(self.setBeamcenterCB)
        hBoxFastDP.addWidget(self.setBeamcenterButton)
        self.beamcenterX_ledit =  QtWidgets.QLineEdit()
        self.beamcenterX_ledit.setText(str(self.parent.beamCenterX_pv.get()))        
        self.beamcenterY_ledit =  QtWidgets.QLineEdit()
        self.beamcenterY_ledit.setText(str(self.parent.beamCenterY_pv.get()))
        hBoxFastDP.addWidget(self.beamcenterX_ledit)
        hBoxFastDP.addWidget(self.beamcenterY_ledit)                
        self.setSpotNodesButton = QtWidgets.QPushButton("Set Spotfinder Nodes")
        self.setSpotNodesButton.clicked.connect(self.setSpotNodesCB)
        self.lockGuiButton = QtWidgets.QPushButton("Lock")
        self.lockGuiButton.clicked.connect(self.lockGuiCB)
        self.unLockGuiButton = QtWidgets.QPushButton("unLock")
        self.unLockGuiButton.clicked.connect(self.unLockGuiCB)
        hBoxSpotfinder.addWidget(self.lockGuiButton)
        hBoxSpotfinder.addWidget(self.unLockGuiButton)                        
        hBoxSpotfinder.addWidget(self.setSpotNodesButton)        
        self.spotNodeEntryList = []
        nodeList = self.getSpotNodeList()        
        for i in range (0,self.spotNodeCount):
          self.spotNodeEntryList.append(QtWidgets.QLineEdit())
          self.spotNodeEntryList[i].setFixedWidth(30)
          self.spotNodeEntryList[i].setText(str(nodeList[i]))          
          hBoxSpotfinder.addWidget(self.spotNodeEntryList[i])
        robotGB = QtWidgets.QGroupBox()
        robotGB.setTitle("Robot")
        hBoxRobot1 = QtWidgets.QHBoxLayout()
        vBoxRobot1 = QtWidgets.QVBoxLayout()
        self.recoverRobotButton = QtWidgets.QPushButton("Recover Robot")
        self.recoverRobotButton.clicked.connect(self.recoverRobotCB)
        self.rebootEMBLButton = QtWidgets.QPushButton("Reboot EMBL")
        self.rebootEMBLButton.clicked.connect(self.rebootEMBL_CB)
        self.restartEMBLButton = QtWidgets.QPushButton("Start EMBL")
        self.restartEMBLButton.clicked.connect(self.restartEMBL_CB)
        self.openGripperButton = QtWidgets.QPushButton("Open Gripper")
        self.openGripperButton.clicked.connect(self.openGripper_CB)
        self.closeGripperButton = QtWidgets.QPushButton("Close Gripper")
        self.closeGripperButton.clicked.connect(self.closeGripper_CB)
        hBoxRobot1.addWidget(self.robotOnCheckBox)
        hBoxRobot1.addWidget(self.topViewCheckOnCheckBox)
        hBoxRobot1.addWidget(self.enableMountCheckBox)        
        hBoxRobot1.addWidget(self.recoverRobotButton)
        hBoxRobot1.addWidget(self.rebootEMBLButton)
        hBoxRobot1.addWidget(self.restartEMBLButton)
        hBoxRobot1.addWidget(self.openGripperButton)
        hBoxRobot1.addWidget(self.closeGripperButton)                        
        vBoxRobot1.addLayout(hBoxRobot1)
        vBoxRobot1.addLayout(hBoxColParams2)        
        robotGB.setLayout(vBoxRobot1)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok,
            Qt.Horizontal, self)
        self.buttons.buttons()[0].clicked.connect(self.screenDefaultsOKCB)
        vBoxColParams1.addLayout(hBoxColParams0)
        vBoxColParams1.addLayout(hBoxColParams1)
        vBoxColParams1.addLayout(hBoxFastDP)
        vBoxColParams1.addLayout(hBoxSpotfinder)        
        vBoxColParams1.addWidget(robotGB)
        vBoxColParams1.addWidget(self.buttons)
        self.setLayout(vBoxColParams1)        
        self.show()


    def getSpotNodeList(self):
      nodeList = []
      for i in range (0,self.spotNodeCount):
        nodeList.append(int(getBlConfig("spotNode"+str(i+1)).split('-')[1]))
      return nodeList
        
        
    def getFastDPNodeList(self):
      nodeList = []
      for i in range (0,self.fastDPNodeCount):
        nodeList.append(int(getBlConfig("fastDPNode"+str(i+1)).split('-')[1]))
      return nodeList

    def setFastDPNodesCB(self):
      comm_s = "fastDPNodes("
      for i in range (0,self.fastDPNodeCount):
        comm_s = comm_s+str(self.fastDPNodeEntryList[i].text())
        if (i==self.fastDPNodeCount-1):
          comm_s = comm_s+")"
        else:
          comm_s = comm_s+","
      logger.info(comm_s)
      self.parent.send_to_server(comm_s)

    def lockGuiCB(self):
      self.parent.send_to_server("lockControl")

    def unLockGuiCB(self):
      self.parent.send_to_server("unlockControl")
      
    def setSpotNodesCB(self):
      comm_s = "spotNodes("
      for i in range (0,self.spotNodeCount):
        comm_s = comm_s+str(self.spotNodeEntryList[i].text())
        if (i==self.spotNodeCount-1):
          comm_s = comm_s+")"
        else:
          comm_s = comm_s+","
      logger.info(comm_s)
      self.parent.send_to_server(comm_s)      

        
    def unmountColdCB(self):
      self.parent.send_to_server("unmountCold()")

    def openPort1CB(self):
      self.parent.send_to_server("openPort(1)")

    def setBeamcenterCB(self):
      self.parent.send_to_server("set_beamcenter (" + str(self.beamcenterX_ledit.text()) + "," + str(self.beamcenterY_ledit.text()) + ")")
      
    def closePortsCB(self):
      self.parent.send_to_server("closePorts()")
      
    def clearMountedSampleCB(self):
      self.parent.send_to_server("clearMountedSample()")

    def recoverRobotCB(self):
      self.parent.aux_send_to_server("recoverRobot()")

    def rebootEMBL_CB(self):
      self.parent.aux_send_to_server("rebootEMBL()")

    def restartEMBL_CB(self):
      self.parent.send_to_server("restartEMBL()")

    def openGripper_CB(self):
      self.parent.send_to_server("openGripper()")

    def closeGripper_CB(self):
      self.parent.send_to_server("closeGripper()")
      
    def homePinsCB(self):
      self.parent.send_to_server("homePins()")
      

    def robotOnCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        setBlConfig("robot_online",1)
      else:
        setBlConfig("robot_online",0)

    def topViewOnCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        setBlConfig(TOP_VIEW_CHECK,1)
      else:
        setBlConfig(TOP_VIEW_CHECK,0)
        
    def vertRasterOnCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        setBlConfig("vertRasterOn",1)
      else:
        setBlConfig("vertRasterOn",0)

    def procRasterOnCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        setBlConfig("rasterProcessFlag",1)
      else:
        setBlConfig("rasterProcessFlag",0)

    def guiRemoteOnCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        setBlConfig("omegaMonitorPV","VAL")
      else:
        setBlConfig("omegaMonitorPV","RBV")
        
    def queueCollectOnCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        setBlConfig("queueCollect",1)
      else:
        setBlConfig("queueCollect",0)

    def enableMountCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        setBlConfig("mountEnabled",1)
      else:
        setBlConfig("mountEnabled",0)

    def screenDefaultsCancelCB(self):
      self.hide()

    def screenDefaultsOKCB(self):
      self.hide()
        

class UserScreenDialog(QFrame):  
    def __init__(self,parent = None):
        self.parent=parent
        QFrame.__init__(self)
        self.setWindowTitle("User Extras")        
        vBoxColParams1 = QtWidgets.QVBoxLayout()
        hBoxColParams1 = QtWidgets.QHBoxLayout()        
        hBoxColParams2 = QtWidgets.QHBoxLayout()
        hBoxColParams25 = QtWidgets.QHBoxLayout()        
        hBoxColParams3 = QtWidgets.QHBoxLayout()        
        govLabel = QtWidgets.QLabel('Set Governor State:')        
        self.SEbutton = QtWidgets.QPushButton("SE")
        self.SEbutton.clicked.connect(self.SEgovCB)
        self.SAbutton = QtWidgets.QPushButton("SA")
        self.SAbutton.clicked.connect(self.SAgovCB)
        self.DAbutton = QtWidgets.QPushButton("DA")
        self.DAbutton.clicked.connect(self.DAgovCB)
        self.BLbutton = QtWidgets.QPushButton("BL")
        self.BLbutton.clicked.connect(self.BLgovCB)
        hBoxColParams1.addWidget(govLabel)
        hBoxColParams1.addWidget(self.SEbutton)
        hBoxColParams1.addWidget(self.SAbutton)
        hBoxColParams1.addWidget(self.DAbutton)
        hBoxColParams1.addWidget(self.BLbutton)        
        govLabel2 = QtWidgets.QLabel('Current Governor State:')                
        self.governorMessage = QtEpicsPVLabel(daq_utils.pvLookupDict["governorMessage"],self,140,highlight_on_change=False)
        hBoxColParams2.addWidget(govLabel2)
        hBoxColParams2.addWidget(self.governorMessage.getEntry())
        
        self.openShutterButton = QtWidgets.QPushButton("Open Photon Shutter")
        self.openShutterButton.clicked.connect(self.parent.openPhotonShutterCB)
        hBoxColParams25.addWidget(self.openShutterButton)        
        robotGB = QtWidgets.QGroupBox()
        robotGB.setTitle("Robot")

        self.unmountColdButton = QtWidgets.QPushButton("Unmount Cold")
        self.unmountColdButton.clicked.connect(self.unmountColdCB)        
        self.testRobotButton = QtWidgets.QPushButton("Test Robot")
        self.testRobotButton.clicked.connect(self.testRobotCB)        
        self.recoverRobotButton = QtWidgets.QPushButton("Recover Robot")
        self.recoverRobotButton.clicked.connect(self.recoverRobotCB)        
        self.dryGripperButton = QtWidgets.QPushButton("Dry Gripper")
        self.dryGripperButton.clicked.connect(self.dryGripperCB)        

        hBoxColParams3.addWidget(self.unmountColdButton)
        hBoxColParams3.addWidget(self.testRobotButton)
        hBoxColParams3.addWidget(self.recoverRobotButton)        
        hBoxColParams3.addWidget(self.dryGripperButton)
        robotGB.setLayout(hBoxColParams3)

        zebraGB = QtWidgets.QGroupBox()
        detGB = QtWidgets.QGroupBox()        
        zebraGB.setTitle("Zebra (Timing)")
        detGB.setTitle("Eiger Detector")
        hBoxDet1 = QtWidgets.QHBoxLayout()
        hBoxDet2 = QtWidgets.QHBoxLayout()        
        vBoxDet1 = QtWidgets.QVBoxLayout()
        self.stopDetButton = QtWidgets.QPushButton("Stop")
        self.stopDetButton.clicked.connect(self.stopDetCB)
        self.rebootDetIocButton = QtWidgets.QPushButton("Reboot Det IOC")
        self.rebootDetIocButton.clicked.connect(self.rebootDetIocCB)
        detStatLabel = QtWidgets.QLabel('Detector Status:')
        self.detMessage_ledit = QtWidgets.QLabel()
        hBoxDet1.addWidget(self.stopDetButton)
        hBoxDet1.addWidget(self.rebootDetIocButton)
        hBoxDet2.addWidget(detStatLabel)
        hBoxDet2.addWidget(self.detMessage_ledit)

        beamGB = QtWidgets.QGroupBox()
        beamGB.setTitle("Beam")
        hBoxBeam1 = QtWidgets.QHBoxLayout()
        hBoxBeam2 = QtWidgets.QHBoxLayout()
        hBoxBeam3 = QtWidgets.QHBoxLayout()        
        vBoxBeam = QtWidgets.QVBoxLayout()
        if (daq_utils.beamline == "fmx"):
          slit1XLabel = QtWidgets.QLabel('Slit 1 X Gap:')
          slit1XLabel.setAlignment(QtCore.Qt.AlignCenter)         
          slit1XRBLabel = QtWidgets.QLabel("Readback:")
          self.slit1XRBVLabel = QtEpicsPVLabel(daq_utils.motor_dict["slit1XGap"] + ".RBV",self,70) 
          slit1XSPLabel = QtWidgets.QLabel("SetPoint:")
          self.slit1XMotor_ledit = QtWidgets.QLineEdit()
          self.slit1XMotor_ledit.returnPressed.connect(self.setSlit1XCB)
          self.slit1XMotor_ledit.setText(str(self.parent.slit1XGapSP_pv.get()))

          slit1YLabel = QtWidgets.QLabel('Slit 1 Y Gap:')
          slit1YLabel.setAlignment(QtCore.Qt.AlignCenter)         
          slit1YRBLabel = QtWidgets.QLabel("Readback:")
          self.slit1YRBVLabel = QtEpicsPVLabel(daq_utils.motor_dict["slit1YGap"] + ".RBV",self,70) 
          slit1YSPLabel = QtWidgets.QLabel("SetPoint:")
          self.slit1YMotor_ledit = QtWidgets.QLineEdit()
          self.slit1YMotor_ledit.setText(str(self.parent.slit1YGapSP_pv.get()))          
          self.slit1YMotor_ledit.returnPressed.connect(self.setSlit1YCB)
        
        sampleFluxLabelDesc = QtWidgets.QLabel("Sample Flux:")
        sampleFluxLabelDesc.setFixedWidth(80)
        self.sampleFluxLabel = QtWidgets.QLabel()
        self.sampleFluxLabel.setText('%E' % self.parent.sampleFluxPV.get())
        hBoxBeam3.addWidget(sampleFluxLabelDesc)
        hBoxBeam3.addWidget(self.sampleFluxLabel)

        if (daq_utils.beamline == "fmx"):        
          hBoxBeam1.addWidget(slit1XLabel)
          hBoxBeam1.addWidget(slit1XRBLabel)
          hBoxBeam1.addWidget(self.slit1XRBVLabel.getEntry())
          hBoxBeam1.addWidget(slit1XSPLabel)        
          hBoxBeam1.addWidget(self.slit1XMotor_ledit)          
          hBoxBeam2.addWidget(slit1YLabel)
          hBoxBeam2.addWidget(slit1YRBLabel)
          hBoxBeam2.addWidget(self.slit1YRBVLabel.getEntry())
          hBoxBeam2.addWidget(slit1YSPLabel)        
          hBoxBeam2.addWidget(self.slit1YMotor_ledit)
          vBoxBeam.addLayout(hBoxBeam1)        
          vBoxBeam.addLayout(hBoxBeam2)
        vBoxBeam.addLayout(hBoxBeam3)        
        beamGB.setLayout(vBoxBeam)
        
        
        vBoxDet1.addLayout(hBoxDet1)
        vBoxDet1.addLayout(hBoxDet2)        
        detGB.setLayout(vBoxDet1)
        hBoxColParams4 = QtWidgets.QHBoxLayout()
        vBoxZebraParams4 = QtWidgets.QVBoxLayout()        
        self.resetZebraButton = QtWidgets.QPushButton("Reset Zebra")
        self.resetZebraButton.clicked.connect(self.resetZebraCB)
        self.rebootZebraButton = QtWidgets.QPushButton("Reboot Zebra IOC")
        self.rebootZebraButton.clicked.connect(self.rebootZebraIOC_CB)
        hBoxColParams5 = QtWidgets.QHBoxLayout()
        self.zebraArmCheckBox = QCheckBox("Arm")
        self.zebraArmCheckBox.setEnabled(False)
        self.zebraPulseCheckBox = QCheckBox("Pulse")
        self.zebraPulseCheckBox.setEnabled(False)
        self.zebraDownloadCheckBox = QCheckBox("Downloading")
        self.zebraDownloadCheckBox.setEnabled(False)
        self.zebraSentTriggerCheckBox = QCheckBox("Trigger Sent")
        self.zebraSentTriggerCheckBox.setEnabled(False)
        self.zebraReturnedTriggerCheckBox = QCheckBox("Trigger Returned")
        self.zebraReturnedTriggerCheckBox.setEnabled(False)
        hBoxColParams4.addWidget(self.resetZebraButton)
        hBoxColParams4.addWidget(self.rebootZebraButton)
        hBoxColParams5.addWidget(self.zebraArmCheckBox)
        hBoxColParams5.addWidget(self.zebraPulseCheckBox)
        hBoxColParams5.addWidget(self.zebraDownloadCheckBox)
        hBoxColParams5.addWidget(self.zebraSentTriggerCheckBox)
        hBoxColParams5.addWidget(self.zebraReturnedTriggerCheckBox)                                
        vBoxZebraParams4.addLayout(hBoxColParams4)
        vBoxZebraParams4.addLayout(hBoxColParams5)        
        zebraGB.setLayout(vBoxZebraParams4)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok,
            Qt.Horizontal, self)
        self.buttons.buttons()[0].clicked.connect(self.userScreenOKCB)

        vBoxColParams1.addLayout(hBoxColParams1)
        vBoxColParams1.addLayout(hBoxColParams2)        
        vBoxColParams1.addLayout(hBoxColParams25)
        vBoxColParams1.addWidget(robotGB)        
        vBoxColParams1.addWidget(zebraGB)
        vBoxColParams1.addWidget(detGB)
        vBoxColParams1.addWidget(beamGB)                

        vBoxColParams1.addWidget(self.buttons)
        self.setLayout(vBoxColParams1)


    def setSlit1XCB(self):
      comm_s = "setSlit1X(" + str(self.slit1XMotor_ledit.text()) + ")"      
      self.parent.send_to_server(comm_s)

    def setSlit1YCB(self):
      comm_s = "setSlit1Y(" + str(self.slit1YMotor_ledit.text()) + ")"            
      self.parent.send_to_server(comm_s)
      
    def unmountColdCB(self):
      self.parent.send_to_server("unmountCold()")

    def testRobotCB(self):
      self.parent.send_to_server("testRobot()")

    def recoverRobotCB(self):
      self.parent.send_to_server("recoverRobot()")

    def dryGripperCB(self):
      self.parent.send_to_server("dryGripper()")
      
    def stopDetCB(self):
      logger.info('stopping detector')
      self.parent.stopDet_pv.put(0)

    def rebootDetIocCB(self):
      logger.info('rebooting detector IOC')
      self.parent.rebootDetIOC_pv.put(1)     # no differences visible, but zebra IOC reboot works, this doesn't! 

    def resetZebraCB(self):
      logger.info('resetting zebra')
      self.parent.resetZebra_pv.put(1)

    def rebootZebraIOC_CB(self):
      logger.info('rebooting zebra IOC')
      self.parent.rebootZebraIOC_pv.put(1)

    def SEgovCB(self):
      self.parent.send_to_server("setGovRobot('SE')")

    def SAgovCB(self):
      self.parent.send_to_server("setGovRobot('SA')")

    def DAgovCB(self):
      self.parent.send_to_server("setGovRobot('DA')")

    def BLgovCB(self):
      self.parent.send_to_server("setGovRobot('BL')")

    def userScreenOKCB(self):
      self.hide()
      
    def screenDefaultsCancelCB(self):
      self.done(QDialog.Rejected)

    def screenDefaultsOKCB(self):
      self.done(QDialog.Accepted)        
      

class ScreenDefaultsDialog(QtWidgets.QDialog):
    def __init__(self,parent = None):
        QtWidgets.QDialog.__init__(self,parent)
        self.parent=parent        
        self.setModal(False)
        self.setWindowTitle("Raster Params")        

        vBoxColParams1 = QtWidgets.QVBoxLayout()

        collectionGB = QtWidgets.QGroupBox()
        collectionGB.setTitle('Collection parameters')

        hBoxColParams2 = QtWidgets.QHBoxLayout()
        colRangeLabel = QtWidgets.QLabel('Oscillation Width:')
        colRangeLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.osc_range_ledit = QtWidgets.QLineEdit() # note, this is for rastering! same name used for data collections
        self.setGuiValues({'osc_range':getBlConfig("rasterDefaultWidth")})
        self.osc_range_ledit.returnPressed.connect(self.screenDefaultsOKCB)                        
        colExptimeLabel = QtWidgets.QLabel('ExposureTime:')
        colExptimeLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.exp_time_ledit = QtWidgets.QLineEdit()
        self.setGuiValues({'exp_time':getBlConfig("rasterDefaultTime")})
        self.exp_time_ledit.returnPressed.connect(self.screenDefaultsOKCB)                
        self.exp_time_ledit.setValidator(QtGui.QDoubleValidator(VALID_EXP_TIMES[daq_utils.beamline]['min'], VALID_EXP_TIMES[daq_utils.beamline]['max'], VALID_EXP_TIMES[daq_utils.beamline]['digits']))
        self.exp_time_ledit.textChanged.connect(self.checkEntryState)

        colTransLabel = QtWidgets.QLabel('Transmission (0.0-1.0):')
        colTransLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.trans_ledit = QtWidgets.QLineEdit()
        self.setGuiValues({'transmission':getBlConfig("rasterDefaultTrans")})
        self.trans_ledit.returnPressed.connect(self.screenDefaultsOKCB)                
        hBoxColParams2.addWidget(colRangeLabel)
        hBoxColParams2.addWidget(self.osc_range_ledit)
        hBoxColParams2.addWidget(colExptimeLabel)
        hBoxColParams2.addWidget(self.exp_time_ledit)
        hBoxColParams2.addWidget(colTransLabel)
        hBoxColParams2.addWidget(self.trans_ledit)
        collectionGB.setLayout(hBoxColParams2)

        dozorGB = QtWidgets.QGroupBox()
        dozorGB.setTitle('Dozor Parameter')
        hBoxColParams2a = QtWidgets.QHBoxLayout()
        dozorSpotLevelLabel = QtWidgets.QLabel('Dozor Spot Level\n(Applies immediately)')
        self.dozorSpotLevel = QComboBox()
        self.dozorSpotLevel.addItems(['5', '6', '7', '8'])
        self.dozorSpotLevel.currentIndexChanged.connect(self.dozorSpotLevelChangedCB)
        hBoxColParams2a.addWidget(dozorSpotLevelLabel)
        hBoxColParams2a.addWidget(self.dozorSpotLevel)
        dozorGB.setLayout(hBoxColParams2a)

        dialsGB = QtWidgets.QGroupBox()
        dialsGB.setTitle('Dials Parameters')
        vBoxDialsParams = QtWidgets.QVBoxLayout()
        hBoxColParams2b = QtWidgets.QHBoxLayout()
        colMinSpotLabel = QtWidgets.QLabel('Min Spot Size:')
        colMinSpotLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.minSpot_ledit = QtWidgets.QLineEdit()
        self.minSpot_ledit.setText(str(getBlConfig("rasterDefaultMinSpotSize")))
        self.minSpot_ledit.returnPressed.connect(self.screenDefaultsOKCB)                
        hBoxColParams2b.addWidget(colMinSpotLabel)
        hBoxColParams2b.addWidget(self.minSpot_ledit)

        self.hBoxRasterLayout2 = QtWidgets.QHBoxLayout()
        rasterTuneLabel = QtWidgets.QLabel('Raster\nTuning')
        self.rasterResoCheckBox = QCheckBox("Constrain Resolution")
        self.rasterResoCheckBox.stateChanged.connect(self.rasterResoCheckCB)
        rasterLowResLabel  = QtWidgets.QLabel('LowRes:')
        self.rasterLowRes = QtWidgets.QLineEdit()
        self.rasterLowRes.setText(str(getBlConfig(RASTER_TUNE_LOW_RES)))
        self.rasterLowRes.returnPressed.connect(self.screenDefaultsOKCB)                
        rasterHighResLabel  = QtWidgets.QLabel('HighRes:')
        self.rasterHighRes = QtWidgets.QLineEdit()
        self.rasterHighRes.setText(str(getBlConfig(RASTER_TUNE_HIGH_RES)))
        self.rasterHighRes.returnPressed.connect(self.screenDefaultsOKCB)                
        if (getBlConfig(RASTER_TUNE_RESO_FLAG) == 1):
          resoFlag = True
        else:
          resoFlag = False
          self.rasterHighRes.setEnabled(False)
          self.rasterLowRes.setEnabled(False)                    
        self.rasterResoCheckBox.setChecked(resoFlag)
        self.rasterIceRingCheckBox = QCheckBox("Ice Ring")
        self.rasterIceRingCheckBox.setChecked(False)
        self.rasterIceRingCheckBox.stateChanged.connect(self.rasterIceRingCheckCB)        
        self.rasterIceRingWidth = QtWidgets.QLineEdit()
        self.rasterIceRingWidth.setText(str(getBlConfig(RASTER_TUNE_ICE_RING_WIDTH)))
        self.rasterIceRingWidth.returnPressed.connect(self.screenDefaultsOKCB)                
        self.rasterIceRingWidth.setEnabled(False)
        if (getBlConfig(RASTER_TUNE_ICE_RING_FLAG) == 1):
          iceRingFlag = True
        else:
          iceRingFlag = False            
        self.rasterIceRingCheckBox.setChecked(iceRingFlag)
        self.hBoxRasterLayout2.addWidget(self.rasterResoCheckBox)
        self.hBoxRasterLayout2.addWidget(rasterLowResLabel)
        self.hBoxRasterLayout2.addWidget(self.rasterLowRes)
        self.hBoxRasterLayout2.addWidget(rasterHighResLabel)
        self.hBoxRasterLayout2.addWidget(self.rasterHighRes)
        self.hBoxRasterLayout2.addWidget(self.rasterIceRingCheckBox)
        self.hBoxRasterLayout2.addWidget(self.rasterIceRingWidth)        

        self.hBoxRasterLayout3 = QtWidgets.QHBoxLayout()
        self.rasterThreshCheckBox = QCheckBox("Tune Threshold")
        if (getBlConfig("rasterThreshFlag") == 1):
          threshFlag = True
        else:
          threshFlag = False
        self.rasterThreshCheckBox.setChecked(threshFlag)
        self.rasterThreshCheckBox.stateChanged.connect(self.rasterThreshCheckCB)
        
        rasterThreshKernSizeLabel =  QtWidgets.QLabel('KernelSize')
        self.rasterThreshKernSize = QtWidgets.QLineEdit()
        self.rasterThreshKernSize.setText(str(getBlConfig("rasterThreshKernSize")))
        self.rasterThreshKernSize.returnPressed.connect(self.screenDefaultsOKCB)                
        rasterThreshSigBckLabel =  QtWidgets.QLabel('SigmaBkrnd')        
        self.rasterThreshSigBckrnd = QtWidgets.QLineEdit()
        self.rasterThreshSigBckrnd.setText(str(getBlConfig("rasterThreshSigBckrnd")))
        self.rasterThreshSigBckrnd.returnPressed.connect(self.screenDefaultsOKCB)                
        rasterThreshSigStrongLabel =  QtWidgets.QLabel('SigmaStrong')                
        self.rasterThreshSigStrong = QtWidgets.QLineEdit()
        self.rasterThreshSigStrong.setText(str(getBlConfig("rasterThreshSigStrong")))
        self.rasterThreshSigStrong.returnPressed.connect(self.screenDefaultsOKCB)                
        self.rasterThreshKernSize.setEnabled(threshFlag)
        self.rasterThreshSigBckrnd.setEnabled(threshFlag)
        self.rasterThreshSigStrong.setEnabled(threshFlag)                
        self.hBoxRasterLayout3.addWidget(self.rasterThreshCheckBox)
        self.hBoxRasterLayout3.addWidget(rasterThreshKernSizeLabel)
        self.hBoxRasterLayout3.addWidget(self.rasterThreshKernSize)
        self.hBoxRasterLayout3.addWidget(rasterThreshSigBckLabel)
        self.hBoxRasterLayout3.addWidget(self.rasterThreshSigBckrnd)
        self.hBoxRasterLayout3.addWidget(rasterThreshSigStrongLabel)
        self.hBoxRasterLayout3.addWidget(self.rasterThreshSigStrong)

        vBoxDialsParams.addLayout(hBoxColParams2b)
        vBoxDialsParams.addLayout(self.hBoxRasterLayout2)
        vBoxDialsParams.addLayout(self.hBoxRasterLayout3)
        dialsGB.setLayout(vBoxDialsParams)

        reprocessRasterButton = QtWidgets.QPushButton("ReProcessRaster") 
        reprocessRasterButton.clicked.connect(self.reprocessRasterRequestCB)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Apply | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.buttons()[1].clicked.connect(self.screenDefaultsOKCB)
        self.buttons.buttons()[0].clicked.connect(self.screenDefaultsCancelCB)
        vBoxColParams1.addWidget(collectionGB)
        vBoxColParams1.addWidget(dozorGB)
        vBoxColParams1.addWidget(dialsGB)
        vBoxColParams1.addWidget(reprocessRasterButton)                        
        vBoxColParams1.addWidget(self.buttons)
        self.setLayout(vBoxColParams1)

    def setGuiValues(self, values):
      for item, value in values.items():
        logger.info('resetting %s to %s' % (item, value))
        if item == 'osc_range':
          self.osc_range_ledit.setText('%.3f' % float(value))
        elif item == 'exp_time':
          self.exp_time_ledit.setText('%.3f' % float(value))
        elif item == 'transmission':
          self.trans_ledit.setText('%.3f' % float(value))
        else:
          logger.error('setGuiValues unknown item: %s value: %s' % (item, value))

    def reprocessRasterRequestCB(self):
      self.parent.eraseCB()
      try:      
        reqID = self.parent.selectedSampleRequest["uid"]
        self.parent.drawPolyRaster(db_lib.getRequestByID(reqID))
        self.parent.send_to_server("reprocessRaster(\""+str(reqID)+"\")")
      except:
        pass
      
        
    def screenDefaultsCancelCB(self):
      self.done(QDialog.Rejected)

    def dozorSpotLevelChangedCB(self, i):
      setBlConfig(RASTER_DOZOR_SPOT_LEVEL, int(self.dozorSpotLevel.itemText(i)))

    def screenDefaultsOKCB(self):
      setBlConfig("rasterDefaultWidth",float(self.osc_range_ledit.text()))
      setBlConfig("rasterDefaultTime",float(self.exp_time_ledit.text()))
      setBlConfig("rasterDefaultTrans",float(self.trans_ledit.text()))
      setBlConfig("rasterDefaultMinSpotSize",float(self.minSpot_ledit.text()))            
      setBlConfig(RASTER_TUNE_LOW_RES,float(self.rasterLowRes.text()))
      setBlConfig(RASTER_TUNE_HIGH_RES,float(self.rasterHighRes.text()))
      setBlConfig(RASTER_TUNE_ICE_RING_WIDTH,float(self.rasterIceRingWidth.text()))
      setBlConfig("rasterThreshKernSize",float(self.rasterThreshKernSize.text()))
      setBlConfig("rasterThreshSigBckrnd",float(self.rasterThreshSigBckrnd.text()))
      setBlConfig("rasterThreshSigStrong",float(self.rasterThreshSigStrong.text()))                  
      if (self.rasterIceRingCheckBox.isChecked()):
        setBlConfig(RASTER_TUNE_ICE_RING_FLAG,1)
      else:
        setBlConfig(RASTER_TUNE_ICE_RING_FLAG,0)          
      if (self.rasterResoCheckBox.isChecked()):
        setBlConfig(RASTER_TUNE_RESO_FLAG,1)
      else:
        setBlConfig(RASTER_TUNE_RESO_FLAG,0)          
    
    def rasterIceRingCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        self.rasterIceRingWidth.setEnabled(True)        
      else:
        self.rasterIceRingWidth.setEnabled(False)          

    def rasterResoCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        setBlConfig(RASTER_TUNE_RESO_FLAG,1)        
        self.rasterLowRes.setEnabled(True)
        self.rasterHighRes.setEnabled(True)                
      else:
        setBlConfig(RASTER_TUNE_RESO_FLAG,0)                
        self.rasterLowRes.setEnabled(False)
        self.rasterHighRes.setEnabled(False)                

    def rasterThreshCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        setBlConfig("rasterThreshFlag",1)
        self.rasterThreshKernSize.setEnabled(True)
        self.rasterThreshSigBckrnd.setEnabled(True)
        self.rasterThreshSigStrong.setEnabled(True)                        
      else:
        setBlConfig("rasterThreshFlag",0)        
        self.rasterThreshKernSize.setEnabled(False)
        self.rasterThreshSigBckrnd.setEnabled(False)
        self.rasterThreshSigStrong.setEnabled(False)                        

    #code below and its application from: https://snorfalorpagus.net/blog/2014/08/09/validating-user-input-in-pyqt4-using-qvalidator/
    def checkEntryState(self, *args, **kwargs):
      sender = self.sender()
      validator = sender.validator()
      state = validator.validate(sender.text(), 0)[0]
      if state == QtGui.QValidator.Intermediate:
          color = '#fff79a' # yellow
      elif state == QtGui.QValidator.Invalid:
          color = '#f6989d' # red
      else:
          color = '#ffffff' # white
      sender.setStyleSheet('QLineEdit { background-color: %s }' % color)


class PuckDialog(QtWidgets.QDialog):
    def __init__(self, parent = None):
        super(PuckDialog, self).__init__(parent)
        self.initData()
        self.initUI()


    def initData(self):
        puckListUnsorted = db_lib.getAllPucks(daq_utils.owner)
        puckList = sorted(puckListUnsorted,key=lambda i: i['name'],reverse=False)
        dewarObj = db_lib.getPrimaryDewar(daq_utils.beamline)
        pucksInDewar = dewarObj['content']
        data = []
#if you have to, you could store the puck_id in the item data
        for i in range(len(puckList)):
          if (puckList[i]["uid"] not in pucksInDewar):
            data.append(puckList[i]["name"])
        self.model = QtGui.QStandardItemModel()
        labels = QStringList(("Name"))
        self.model.setHorizontalHeaderLabels(labels)
        for i in range(len(data)):
            name = QtGui.QStandardItem(data[i])
            self.model.appendRow(name)


    def initUI(self):
        self.tv = QtWidgets.QListView(self)
        self.tv.setModel(self.model)
        self.tv.doubleClicked[QModelIndex].connect(self.containerOKCB)
        behavior = QtWidgets.QAbstractItemView.SelectRows
        self.tv.setSelectionBehavior(behavior)
        
        self.label = QtWidgets.QLabel(self)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.buttons()[0].clicked.connect(self.containerOKCB)
        self.buttons.buttons()[1].clicked.connect(self.containerCancelCB)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tv) 
        layout.addWidget(self.label)
        layout.addWidget(self.buttons)
        self.setLayout(layout)        
        self.tv.clicked.connect(self.onClicked)
            
    def containerOKCB(self):
      selmod = self.tv.selectionModel()
      selection = selmod.selection()
      indexes = selection.indexes()
      if (indexes != []):
        i = 0
        item = self.model.itemFromIndex(indexes[i])
        text = str(item.text())
        self.label.setText(text)      
        self.accept()
        self.puckName = text
      else:
        text = ""
        self.reject()
        self.puckName = text
      

    def containerCancelCB(self):
      text = ""
      self.reject()
      self.puckName = text

        
    def onClicked(self, idx):
      item = self.model.itemFromIndex(idx)        
      text = str(item.text())

    @staticmethod
    def getPuckName(parent = None):
        dialog = PuckDialog(parent)
        result = dialog.exec_()
        return (dialog.puckName, result == QDialog.Accepted)


class DewarDialog(QtWidgets.QDialog):
    def __init__(self, parent = None,action="add"):
        super(DewarDialog, self).__init__(parent)
        self.pucksPerDewarSector = 3
        self.dewarSectors = 8
        self.action = action
        self.parent=parent

        self.initData()
        self.initUI()

    def initData(self):
      dewarObj = db_lib.getPrimaryDewar(daq_utils.beamline)
      puckLocs = dewarObj['content']
      self.data = []
      for i in range(len(puckLocs)):
        if (puckLocs[i] != ""):
          owner = db_lib.getContainerByID(puckLocs[i])["owner"]
          self.data.append(db_lib.getContainerNameByID(puckLocs[i]))
        else:
          self.data.append("Empty")
      logger.info(self.data)


    def initUI(self):
        layout = QtWidgets.QVBoxLayout()
        headerLabelLayout = QtWidgets.QHBoxLayout()
        aLabel = QtWidgets.QLabel("A")
        aLabel.setFixedWidth(15)
        headerLabelLayout.addWidget(aLabel)
        bLabel = QtWidgets.QLabel("B")
        bLabel.setFixedWidth(10)
        headerLabelLayout.addWidget(bLabel)
        cLabel = QtWidgets.QLabel("C")
        cLabel.setFixedWidth(10)
        headerLabelLayout.addWidget(cLabel)
        layout.addLayout(headerLabelLayout)
        self.allButtonList = [None]*(self.dewarSectors*self.pucksPerDewarSector)
        for i in range (0,self.dewarSectors):
          rowLayout = QtWidgets.QHBoxLayout()
          numLabel = QtWidgets.QLabel(str(i+1))
          rowLayout.addWidget(numLabel)
          for j in range (0,self.pucksPerDewarSector):
            dataIndex = (i*self.pucksPerDewarSector)+j            
            self.allButtonList[dataIndex] = QtWidgets.QPushButton((str(self.data[dataIndex])))
            self.allButtonList[dataIndex].clicked.connect(functools.partial(self.on_button,str(dataIndex)))
            rowLayout.addWidget(self.allButtonList[dataIndex])
          layout.addLayout(rowLayout)
        cancelButton = QtWidgets.QPushButton("Done")        
        cancelButton.clicked.connect(self.containerCancelCB)
        layout.addWidget(cancelButton)
        self.setLayout(layout)        
            
    def on_button(self, n):
      if (self.action == "remove"):
        self.dewarPos = n
        db_lib.removePuckFromDewar(daq_utils.beamline,int(n))
        self.allButtonList[int(n)].setText("Empty")
        self.parent.treeChanged_pv.put(1)
      else:
        self.dewarPos = n
        self.accept()


    def containerCancelCB(self):
      self.dewarPos = 0
      self.reject()

    @staticmethod
    def getDewarPos(parent = None,action="add"):
        dialog = DewarDialog(parent,action)
        result = dialog.exec_()
        return (dialog.dewarPos, result == QDialog.Accepted)


class DewarTree(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super(DewarTree, self).__init__(parent)
        self.pucksPerDewarSector = 3
        self.dewarSectors = 8
        self.parent=parent
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setAnimated(True)
        self.model = QtGui.QStandardItemModel()
        self.model.itemChanged.connect(self.queueSelectedSample)
        self.isExpanded = 1

    def keyPressEvent(self, event):
      if (event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace):
        self.deleteSelectedCB(0)
      else:
        super(DewarTree,self).keyPressEvent(event)  

    def refreshTree(self):
      self.parent.dewarViewToggleCheckCB()

    def refreshTreeDewarView(self):
        startTime = time.time()
        selectedIndex = None
        mountedIndex = None
        selectedSampleIndex = None
        puck = ""
        collectionRunning = False
        self.model.clear()
        st = time.time()
        dewarContents = db_lib.getContainerByName(daq_utils.primaryDewarName,daq_utils.beamline)['content']
        for i in range (0,len(dewarContents)): #dewar contents is the list of puck IDs
          parentItem = self.model.invisibleRootItem()
          if (dewarContents[i]==""):
            puck = ""
            puckName = ""
          else:
            st = time.time()
            if (dewarContents[i] not in containerDict):
              puck = db_lib.getContainerByID(dewarContents[i])
              containerDict[dewarContents[i]] = puck
            else:
              puck = containerDict[dewarContents[i]]
            puckName = puck["name"]
          index_s = "%d%s" % ((i)/self.pucksPerDewarSector+1,chr(((i)%self.pucksPerDewarSector)+ord('A')))
          item = QtGui.QStandardItem(QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"), QString(index_s + " " + puckName))
          item.setData(puckName,32)
          item.setData("container",33)          
          parentItem.appendRow(item)
          parentItem = item
          if (puck != "" and puckName != "private"):
            puckContents = puck['content']
            puckSize = len(puckContents)
            for j in range (0,len(puckContents)):#should be the list of samples
              if (puckContents[j] != ""):
                st = time.time()
                if (puckContents[j] not in sampleNameDict):
                  sampleName = db_lib.getSampleNamebyID(puckContents[j])
                  sampleNameDict[puckContents[j]] = sampleName
                else:
                  sampleName = sampleNameDict[puckContents[j]]
                position_s = str(j+1) + "-" + sampleName
                item = QtGui.QStandardItem(QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"), QString(position_s))
                item.setData(puckContents[j],32) #just stuck sampleID there, but negate it to diff from reqID
                item.setData("sample",33)
                if (puckContents[j] == self.parent.mountedPin_pv.get()):
                  item.setForeground(QtGui.QColor('red'))       
                  font = QtGui.QFont()
                  font.setItalic(True)
                  font.setOverline(True)
                  font.setUnderline(True)
                  item.setFont(font)
                parentItem.appendRow(item)
                if (puckContents[j] == self.parent.mountedPin_pv.get()):
                  mountedIndex = self.model.indexFromItem(item)
                if (puckContents[j] == self.parent.selectedSampleID): #looking for the selected item
                  logger.info("found " + str(self.parent.SelectedItemData))
                  selectedSampleIndex = self.model.indexFromItem(item)
                st = time.time()
                sampleRequestList = db_lib.getRequestsBySampleID(puckContents[j])
                for k in range(len(sampleRequestList)):
                  if not ("protocol" in sampleRequestList[k]["request_obj"]):
                    continue
                  col_item = QtGui.QStandardItem(QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"), QString(sampleRequestList[k]["request_obj"]["file_prefix"]+"_"+sampleRequestList[k]["request_obj"]["protocol"]))
                  col_item.setData(sampleRequestList[k]["uid"],32)
                  col_item.setData("request",33)                  
                  col_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
                  if (sampleRequestList[k]["priority"] == 99999):
                    col_item.setCheckState(Qt.Checked)
                    col_item.setBackground(QtGui.QColor('green'))
                    selectedIndex = self.model.indexFromItem(col_item) ##attempt to leave it on the request after collection
                    
                    collectionRunning = True
                    self.parent.refreshCollectionParams(sampleRequestList[k])
                  elif (sampleRequestList[k]["priority"] > 0):
                    col_item.setCheckState(Qt.Checked)
                    col_item.setBackground(QtGui.QColor('white'))
                  elif (sampleRequestList[k]["priority"]< 0):
                    col_item.setCheckable(False)
                    col_item.setBackground(QtGui.QColor('cyan'))
                  else:
                    col_item.setCheckState(Qt.Unchecked)
                    col_item.setBackground(QtGui.QColor('white'))
                  item.appendRow(col_item)
                  if (sampleRequestList[k]["uid"] == self.parent.SelectedItemData): #looking for the selected item, this is a request
                    selectedIndex = self.model.indexFromItem(col_item)
              else : #this is an empty spot, no sample
                position_s = str(j+1)
                item = QtGui.QStandardItem(QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"), QString(position_s))
                item.setData("",32)
                parentItem.appendRow(item)
        self.setModel(self.model)
        if (selectedSampleIndex != None and collectionRunning == False):
          self.setCurrentIndex(selectedSampleIndex)
          if (mountedIndex != None):
            self.model.itemFromIndex(mountedIndex).setForeground(QtGui.QColor('red'))       
            font = QtGui.QFont()
            font.setUnderline(True)
            font.setItalic(True)
            font.setOverline(True)
            self.model.itemFromIndex(mountedIndex).setFont(font)
          self.parent.row_clicked(selectedSampleIndex)
        elif (selectedSampleIndex == None and collectionRunning == False):
          if (mountedIndex != None):
            self.setCurrentIndex(mountedIndex)
            self.model.itemFromIndex(mountedIndex).setForeground(QtGui.QColor('red'))       
            font = QtGui.QFont()
            font.setUnderline(True)
            font.setItalic(True)
            font.setOverline(True)
            self.model.itemFromIndex(mountedIndex).setFont(font)
            self.parent.row_clicked(mountedIndex)
        else:
          pass
        if (selectedIndex != None and collectionRunning == False):
          self.setCurrentIndex(selectedIndex)
          self.parent.row_clicked(selectedIndex)
        if (collectionRunning == True):
          if (mountedIndex != None):
            self.setCurrentIndex(mountedIndex)
        if (self.isExpanded):
          self.expandAll()
        else:
          self.collapseAll()
        self.scrollTo(self.currentIndex(),QAbstractItemView.PositionAtCenter)
        logger.info("refresh time = " + str(time.time()-startTime))


    def refreshTreePriorityView(self): #"item" is a sample, "col_items" are requests which are children of samples.
        collectionRunning = False
        selectedIndex = None
        mountedIndex = None
        selectedSampleIndex = None
        self.model.clear()
        self.orderedRequests = db_lib.getOrderedRequestList(daq_utils.beamline)
        dewarContents = db_lib.getContainerByName(daq_utils.primaryDewarName,daq_utils.beamline)['content']
        maxPucks = len(dewarContents)
        requestedSampleList = []
        mountedPin = self.parent.mountedPin_pv.get()
        for i in range(len(self.orderedRequests)): # I need a list of samples for parent nodes
          if (self.orderedRequests[i]["sample"] not in requestedSampleList):
            requestedSampleList.append(self.orderedRequests[i]["sample"])
        for i in range(len(requestedSampleList)):
          sample = db_lib.getSampleByID(requestedSampleList[i])
          owner = sample["owner"]
          parentItem = self.model.invisibleRootItem()
          nodeString = QString(str(db_lib.getSampleNamebyID(requestedSampleList[i])))
          item = QtGui.QStandardItem(QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"), nodeString)
          item.setData(requestedSampleList[i],32)
          item.setData("sample",33)          
          if (requestedSampleList[i] == mountedPin):
            item.setForeground(QtGui.QColor('red'))       
            font = QtGui.QFont()
            font.setItalic(True)
            font.setOverline(True)
            font.setUnderline(True)
            item.setFont(font)
          parentItem.appendRow(item)
          if (requestedSampleList[i] == mountedPin):
            mountedIndex = self.model.indexFromItem(item)
          if (requestedSampleList[i] == self.parent.selectedSampleID): #looking for the selected item
            selectedSampleIndex = self.model.indexFromItem(item)
          parentItem = item
          for k in range(len(self.orderedRequests)):
            if (self.orderedRequests[k]["sample"] == requestedSampleList[i]):
              col_item = QtGui.QStandardItem(QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"), QString(self.orderedRequests[k]["request_obj"]["file_prefix"]+"_"+self.orderedRequests[k]["request_obj"]["protocol"]))
              col_item.setData(self.orderedRequests[k]["uid"],32)
              col_item.setData("request",33)                  
              col_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable)
              if (self.orderedRequests[k]["priority"] == 99999):
                col_item.setCheckState(Qt.Checked)
                col_item.setBackground(QtGui.QColor('green'))
                collectionRunning = True
                self.parent.refreshCollectionParams(self.orderedRequests[k])

              elif (self.orderedRequests[k]["priority"] > 0):
                col_item.setCheckState(Qt.Checked)
                col_item.setBackground(QtGui.QColor('white'))
              elif (self.orderedRequests[k]["priority"]< 0):
                col_item.setCheckable(False)                
                col_item.setBackground(QtGui.QColor('cyan'))
              else:
                col_item.setCheckState(Qt.Unchecked)
                col_item.setBackground(QtGui.QColor('white'))
              item.appendRow(col_item)
              if (self.orderedRequests[k]["uid"] == self.parent.SelectedItemData): #looking for the selected item
                selectedIndex = self.model.indexFromItem(col_item)
        self.setModel(self.model)
        if (selectedSampleIndex != None and collectionRunning == False):
          self.setCurrentIndex(selectedSampleIndex)
          self.parent.row_clicked(selectedSampleIndex)
        elif (selectedSampleIndex == None and collectionRunning == False):
          if (mountedIndex != None):
            self.setCurrentIndex(mountedIndex)
            self.parent.row_clicked(mountedIndex)
        else:
          pass

        if (selectedIndex != None and collectionRunning == False):
          self.setCurrentIndex(selectedIndex)
          self.parent.row_clicked(selectedIndex)
        self.scrollTo(self.currentIndex(),QAbstractItemView.PositionAtCenter)
        self.expandAll()


    def queueSelectedSample(self,item):
        reqID = str(item.data(32))
        checkedSampleRequest = db_lib.getRequestByID(reqID) #line not needed???
        if (item.checkState() == Qt.Checked):
          db_lib.updatePriority(reqID,5000)
        else:
          db_lib.updatePriority(reqID,0)
        item.setBackground(QtGui.QColor('white'))
        self.parent.treeChanged_pv.put(self.parent.processID) #the idea is touch the pv, but have this gui instance not refresh


    def queueAllSelectedCB(self):
      selmod = self.selectionModel()
      selection = selmod.selection()
      indexes = selection.indexes()
      for i in range(len(indexes)):
        item = self.model.itemFromIndex(indexes[i])
        itemData = str(item.data(32))
        itemDataType = str(item.data(33))
        if (itemDataType == "request"): 
          selectedSampleRequest = db_lib.getRequestByID(itemData)
          db_lib.updatePriority(itemData,5000)
      self.parent.treeChanged_pv.put(1)


    def deQueueAllSelectedCB(self):
      selmod = self.selectionModel()
      selection = selmod.selection()
      indexes = selection.indexes()
      for i in range(len(indexes)):
        item = self.model.itemFromIndex(indexes[i])
        itemData = str(item.data(32))
        itemDataType = str(item.data(33))
        if (itemDataType == "request"): 
          selectedSampleRequest = db_lib.getRequestByID(itemData)
          db_lib.updatePriority(itemData,0)
      self.parent.treeChanged_pv.put(1)


    def confirmDelete(self):
      quit_msg = "Are you sure you want to delete all requests?"
      self.parent.timerHutch.stop()
      self.parent.timerSample.stop()      
      reply = QtWidgets.QMessageBox.question(self, 'Message',quit_msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
      self.parent.timerSample.start(0)            
      self.parent.timerHutch.start(HUTCH_TIMER_DELAY)      
      if reply == QtWidgets.QMessageBox.Yes:
        return(1)
      else:
        return(0)
        

    def deleteSelectedCB(self,deleteAll):
      if (deleteAll):
        if (not self.confirmDelete()):
          return 
        self.selectAll()            
      selmod = self.selectionModel()
      selection = selmod.selection()
      indexes = selection.indexes()
      progressInc = 100.0/float(len(indexes))
      self.parent.progressDialog.setWindowTitle("Deleting Requests")
      self.parent.progressDialog.show()
      for i in range(len(indexes)):
        self.parent.progressDialog.setValue(int((i+1)*progressInc))
        item = self.model.itemFromIndex(indexes[i])
        itemData = str(item.data(32))
        itemDataType = str(item.data(33))
        if (itemDataType == "request"): 
          selectedSampleRequest = db_lib.getRequestByID(itemData)
          self.selectedSampleID = selectedSampleRequest["sample"]
          db_lib.deleteRequest(selectedSampleRequest["uid"])
          if (selectedSampleRequest["request_obj"]["protocol"] == "raster" or selectedSampleRequest["request_obj"]["protocol"] == "stepRaster" or selectedSampleRequest["request_obj"]["protocol"] == "specRaster"):
            for i in range(len(self.parent.rasterList)):
              if (self.parent.rasterList[i] != None):
                if (self.parent.rasterList[i]["uid"] == selectedSampleRequest["uid"]):
                  self.parent.scene.removeItem(self.parent.rasterList[i]["graphicsItem"])
                  self.parent.rasterList[i] = None
          if (selectedSampleRequest["request_obj"]["protocol"] == "vector" or selectedSampleRequest["request_obj"]["protocol"] == "stepVector"):
            self.parent.clearVectorCB()
      self.parent.progressDialog.close()
      self.parent.treeChanged_pv.put(1)
      

    def expandAllCB(self):
      self.expandAll()
      self.isExpanded = 1

    def collapseAllCB(self):
      self.collapseAll()
      self.isExpanded = 0



class DataLocInfo(QtWidgets.QGroupBox):

    def __init__(self,parent=None):
        QGroupBox.__init__(self,parent)
        self.parent = parent
        self.setTitle("Data Location")
        self.vBoxDPathParams1 = QtWidgets.QVBoxLayout()
        self.hBoxDPathParams1 = QtWidgets.QHBoxLayout()
        self.basePathLabel = QtWidgets.QLabel('Base Path:')
        self.base_path_ledit = QtWidgets.QLabel() #leave editable for now
        self.base_path_ledit.setText(os.getcwd())
        self.base_path_ledit.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        #self.base_path_ledit.textChanged[str].connect(self.basePathTextChanged)
        self.browseBasePathButton = QtWidgets.QPushButton("Browse...") 
        self.browseBasePathButton.setEnabled(False)
        #self.browseBasePathButton.clicked.connect(self.parent.popBaseDirectoryDialogCB)
        self.hBoxDPathParams1.addWidget(self.basePathLabel)
        self.hBoxDPathParams1.addWidget(self.base_path_ledit)
        self.hBoxDPathParams1.addWidget(self.browseBasePathButton)
        self.hBoxDPathParams2 = QtWidgets.QHBoxLayout()
        self.dataPrefixLabel = QtWidgets.QLabel('Data Prefix:\n(%s Char Limit)' % VALID_PREFIX_LENGTH)
        self.prefix_ledit = QtWidgets.QLineEdit()
        self.prefix_ledit.textChanged[str].connect(self.prefixTextChanged)
        self.prefix_ledit.setValidator(QRegExpValidator(QRegExp(VALID_PREFIX_NAME), self.prefix_ledit))
        self.hBoxDPathParams2.addWidget(self.dataPrefixLabel)
        self.hBoxDPathParams2.addWidget(self.prefix_ledit)
        self.dataNumstartLabel = QtWidgets.QLabel('File Number Start:')
        self.file_numstart_ledit = QtWidgets.QLineEdit()
        self.file_numstart_ledit.setFixedWidth(50)
        self.hBoxDPathParams3 = QtWidgets.QHBoxLayout()
        self.dataPathLabel = QtWidgets.QLabel('Data Path:')
        self.dataPath_ledit = QtWidgets.QLineEdit()
        self.dataPath_ledit.setFrame(False)
        self.dataPath_ledit.setReadOnly(True)
        self.hBoxDPathParams3.addWidget(self.dataPathLabel)
        self.hBoxDPathParams3.addWidget(self.dataPath_ledit)
        self.hBoxDPathParams2.addWidget(self.dataNumstartLabel)
        self.hBoxDPathParams2.addWidget(self.file_numstart_ledit)
        self.vBoxDPathParams1.addLayout(self.hBoxDPathParams1)
        self.vBoxDPathParams1.addLayout(self.hBoxDPathParams2)
        self.vBoxDPathParams1.addLayout(self.hBoxDPathParams3)
        self.setLayout(self.vBoxDPathParams1)


    def basePathTextChanged(self,text):
      prefix = self.prefix_ledit.text()
      self.setDataPath_ledit(text+"/" + str(daq_utils.getVisitName()) + "/"+prefix+"/#/")

    def prefixTextChanged(self,text):
      prefix = self.prefix_ledit.text()
      try:
        runNum = db_lib.getSampleRequestCount(self.parent.selectedSampleID)
      except KeyError:
        logger.error('just setting a value of 1 for now')
        runNum = 1
      try:
        (puckPosition,samplePositionInContainer,containerID) = db_lib.getCoordsfromSampleID(daq_utils.beamline,self.parent.selectedSampleID)
      except IndexError:
        logger.error('IndexError returning')
        return
      self.setDataPath_ledit(self.base_path_ledit.text()+"/"+ str(daq_utils.getVisitName()) + "/"+prefix+"/"+str(runNum+1)+"/"+db_lib.getContainerNameByID(containerID)+"_"+str(samplePositionInContainer+1)+"/")      

    def setFileNumstart_ledit(self,s):
      self.file_numstart_ledit.setText(s)

    def setFilePrefix_ledit(self,s):
      self.prefix_ledit.setText(s)

    def setBasePath_ledit(self,s):
      self.base_path_ledit.setText(s)

    def setDataPath_ledit(self,s):
      self.dataPath_ledit.setText(s)



class RasterCell(QtWidgets.QGraphicsRectItem):

    def __init__(self,x,y,w,h,topParent):
      super(RasterCell,self).__init__(x,y,w,h,None)
      self.topParent = topParent


def isInCell(position, item):
    if item.contains(position):
        return True
    return False

class RasterGroup(QtWidgets.QGraphicsItemGroup):
    def __init__(self,parent = None):
        super(RasterGroup, self).__init__()
        self.parent=parent
        self.setAcceptHoverEvents(True)


    def mousePressEvent(self, e):
      super(RasterGroup, self).mousePressEvent(e)
      logger.info("mouse pressed on group")
      for i in range(len(self.parent.rasterList)):
        if (self.parent.rasterList[i] != None):
          if (self.parent.rasterList[i]["graphicsItem"].isSelected()):
            logger.info("found selected raster")
            self.parent.SelectedItemData = self.parent.rasterList[i]["uid"]
            self.parent.treeChanged_pv.put(1)
      if (self.parent.vidActionRasterExploreRadio.isChecked()):
          for cell in self.childItems():
              if isInCell(e.pos(), cell):
                  if (cell.data(0) != None):
                      spotcount = cell.data(0)
                      filename = cell.data(1)
                      d_min = cell.data(2)
                      intensity = cell.data(3)
                      if (self.parent.albulaDispCheckBox.isChecked()):
                          if (filename != "empty"):
                              albulaUtils.albulaDispFile(filename)
                      if not (self.parent.rasterExploreDialog.isVisible()):
                          self.parent.rasterExploreDialog.show()
                      self.parent.rasterExploreDialog.setSpotCount(spotcount)
                      self.parent.rasterExploreDialog.setTotalIntensity(intensity)
                      self.parent.rasterExploreDialog.setResolution(d_min)
                      groupList = self.childItems()
                      for i in range (0,len(groupList)):
                          groupList[i].setPen(self.parent.redPen)
                      cell.setPen(self.parent.yellowPen)

      else:
        super(RasterGroup, self).mousePressEvent(e)



    def mouseMoveEvent(self, e):

        if e.buttons() == QtCore.Qt.LeftButton:
          pass
        if e.buttons() == QtCore.Qt.RightButton:
          pass

        super(RasterGroup, self).mouseMoveEvent(e)
        logger.info("pos " + str(self.pos()))

    def mouseReleaseEvent(self, e):
        super(RasterGroup, self).mouseReleaseEvent(e)
        if e.button() == QtCore.Qt.LeftButton:
          pass
        if e.button() == QtCore.Qt.RightButton:
          pass

    def hoverMoveEvent(self, e):
        super(RasterGroup, self).hoverEnterEvent(e)
        for cell in self.childItems():
            if isInCell(e.scenePos(), cell):
                if (cell.data(0) != None):
                    spotcount = cell.data(0)
                    d_min = cell.data(2)
                    intensity = cell.data(3)
                    if not (self.parent.rasterExploreDialog.isVisible()):
                        self.parent.rasterExploreDialog.show()
                    self.parent.rasterExploreDialog.setSpotCount(spotcount)
                    self.parent.rasterExploreDialog.setTotalIntensity(intensity)
                    self.parent.rasterExploreDialog.setResolution(d_min)


class ControlMain(QtWidgets.QMainWindow):
#1/13/15 - are these necessary?
    Signal = QtCore.Signal()
    refreshTreeSignal = QtCore.Signal()
    serverMessageSignal = QtCore.Signal(str)
    serverPopupMessageSignal = QtCore.Signal(str)
    programStateSignal = QtCore.Signal(str)
    pauseButtonStateSignal = QtCore.Signal(str)    


    xrecRasterSignal = QtCore.Signal(str)
    choochResultSignal = QtCore.Signal(str)
    energyChangeSignal = QtCore.Signal(float)
    mountedPinSignal = QtCore.Signal(int)
    beamSizeSignal = QtCore.Signal(float)
    controlMasterSignal = QtCore.Signal(int)
    zebraArmStateSignal = QtCore.Signal(int)
    govRobotSeReachSignal = QtCore.Signal(int)
    govRobotSaReachSignal = QtCore.Signal(int)
    govRobotDaReachSignal = QtCore.Signal(int)
    govRobotBlReachSignal = QtCore.Signal(int)
    detMessageSignal = QtCore.Signal(str)
    sampleFluxSignal = QtCore.Signal(float)
    zebraPulseStateSignal = QtCore.Signal(int)
    stillModeStateSignal = QtCore.Signal(int)
    zebraDownloadStateSignal = QtCore.Signal(int)
    zebraSentTriggerStateSignal = QtCore.Signal(int)
    zebraReturnedTriggerStateSignal = QtCore.Signal(int)
    fastShutterSignal = QtCore.Signal(float)
    gripTempSignal = QtCore.Signal(float)
    ringCurrentSignal = QtCore.Signal(float)
    beamAvailableSignal = QtCore.Signal(float)
    sampleExposedSignal = QtCore.Signal(float)
    sampMoveSignal = QtCore.Signal(int, str)
    roiChangeSignal = QtCore.Signal(str)
    highMagCursorChangeSignal = QtCore.Signal(str)
    lowMagCursorChangeSignal = QtCore.Signal(str)
    cryostreamTempSignal = QtCore.Signal(str)

    def __init__(self):
        super(ControlMain, self).__init__()
        self.SelectedItemData = "" #attempt to know what row is selected
        self.popUpMessageInit = 1 # I hate these next two, but I don't want to catch old messages. Fix later, maybe.
        self.textWindowMessageInit = 1
        self.processID = os.getpid()
        self.popupMessage = QtWidgets.QErrorMessage(self)
        self.popupMessage.setStyleSheet("background-color: red")
        self.popupMessage.setModal(False)
        self.groupName = "skinner"
        self.scannerType = getBlConfig("scannerType")
        self.vectorStart = None
        self.vectorEnd = None
        self.staffScreenDialog = None
        self.centerMarkerCharSize = 20
        self.centerMarkerCharOffsetX = 12
        self.centerMarkerCharOffsetY = 18
        self.currentRasterCellList = []
        self.redPen = QtGui.QPen(QtCore.Qt.red)
        self.bluePen = QtGui.QPen(QtCore.Qt.blue)
        self.yellowPen = QtGui.QPen(QtCore.Qt.yellow)                                
        self.initUI()
        self.zoom1FrameRatePV = PV(daq_utils.pvLookupDict["zoom1FrameRate"])
        self.zoom2FrameRatePV = PV(daq_utils.pvLookupDict["zoom2FrameRate"])
        self.zoom3FrameRatePV = PV(daq_utils.pvLookupDict["zoom3FrameRate"])
        self.zoom4FrameRatePV = PV(daq_utils.pvLookupDict["zoom4FrameRate"])        
        self.sampleFluxPV = PV(daq_utils.pvLookupDict["sampleFlux"])        
        self.beamFlux_pv = PV(daq_utils.pvLookupDict["flux"])
        self.stillMode_pv = PV(daq_utils.pvLookupDict["stillMode"])
        self.standardMode_pv = PV(daq_utils.pvLookupDict["standardMode"])        
        self.lowMagCursorX_pv = PV(daq_utils.pvLookupDict["lowMagCursorX"])
        self.lowMagCursorY_pv = PV(daq_utils.pvLookupDict["lowMagCursorY"])
        self.highMagCursorX_pv = PV(daq_utils.pvLookupDict["highMagCursorX"])
        self.highMagCursorY_pv = PV(daq_utils.pvLookupDict["highMagCursorY"])
        self.fastShutterOpenPos_pv = PV(daq_utils.pvLookupDict["fastShutterOpenPos"])
        self.gripTemp_pv = PV(daq_utils.pvLookupDict["gripTemp"])
        self.cryostreamTemp_pv = PV(cryostreamTempPV[daq_utils.beamline])
        if (daq_utils.beamline == "fmx"):        
          self.slit1XGapSP_pv = PV(daq_utils.motor_dict["slit1XGap"] + ".VAL")
          self.slit1YGapSP_pv = PV(daq_utils.motor_dict["slit1YGap"] + ".VAL")        
        ringCurrentPvName = "SR:C03-BI{DCCT:1}I:Real-I"
        self.ringCurrent_pv = PV(ringCurrentPvName)

        self.beamAvailable_pv = PV(daq_utils.pvLookupDict["beamAvailable"])
        self.sampleExposed_pv = PV(daq_utils.pvLookupDict["exposing"])
        
        self.beamSize_pv = PV(daq_utils.beamlineComm + "size_mode")
        self.energy_pv = PV(daq_utils.motor_dict["energy"]+".RBV")
        self.rasterStepDefs = {"Coarse":20.0,"Fine":10.0,"VFine":5.0}
        self.createSampleTab()
        
        self.initCallbacks()
        if (self.scannerType != "PI"):                            
          self.motPos = {"x":self.sampx_pv.get(),"y":self.sampy_pv.get(),"z":self.sampz_pv.get(),"omega":self.omega_pv.get()}
        else:
          self.motPos = {"x":self.sampx_pv.get(),"y":self.sampy_pv.get(),"z":self.sampz_pv.get(),"omega":self.omega_pv.get(),"fineX":self.sampFineX_pv.get(),"fineY":self.sampFineY_pv.get(),"fineZ":self.sampFineZ_pv.get()}                    
        self.dewarTree.refreshTreeDewarView()
        if (self.mountedPin_pv.get() == ""):
          mountedPin = db_lib.beamlineInfo(daq_utils.beamline, 'mountedSample')["sampleID"]
          self.mountedPin_pv.put(mountedPin)
        self.rasterExploreDialog = RasterExploreDialog()
        self.userScreenDialog = UserScreenDialog(self)        
        self.detDistMotorEntry.getEntry().setText(self.detDistRBVLabel.getEntry().text()) #this is to fix the current val being overwritten by reso
        self.proposalID = -999999
        if (len(sys.argv)>1):
          if (sys.argv[1] == "master"):
            self.changeControlMasterCB(1)
            self.controlMasterCheckBox.setChecked(True)            
        self.XRFInfoDict = self.parseXRFTable() #I don't like this


    def setGuiValues(self, values):
      for item, value in values.items():
        logger.info('resetting %s to %s' % (item, value))
        if item == 'osc_start':
          self.osc_start_ledit.setText('%.3f'% float(value))
        elif item == 'osc_end':
          self.osc_end_ledit.setText('%.3f' % float(value))
        elif item == 'osc_range':
          self.osc_range_ledit.setText('%.3f' % float(value))
        elif item == 'img_width':
          self.img_width_ledit.setText('%.3f' % float(value))
        elif item == 'exp_time':
          self.exp_time_ledit.setText('%.3f' % float(value))
        elif item == 'transmission':
          self.transmission_ledit.setText('%.3f' % float(value))
        elif item == 'resolution':
          self.resolution_ledit.setText('%.2f' % float(value))
        else:
          logger.error('setGuiValues unknown item: %s value: %s' % (item, value))

    def parseXRFTable(self):
      XRFFile = open(os.environ["CONFIGDIR"] + "/XRF-AMX_simple.txt")
      XRFInfoDict = {}
      for line in XRFFile.readlines():
        tokens = line.split()
        XRFInfoDict[tokens[0]] = int(float(tokens[5])*100)
      XRFFile.close()
      return XRFInfoDict
        


    def closeEvent(self, evnt):
       evnt.accept()
       sys.exit() #doing this to close any windows left open

      
    def initVideo2(self,frequency):
      self.captureHighMag=cv2.VideoCapture(daq_utils.highMagCamURL)
      logger.debug('highMagCamURL: "' + daq_utils.highMagCamURL + '"')

    def initVideo4(self,frequency):
      self.captureHighMagZoom=cv2.VideoCapture(daq_utils.highMagZoomCamURL)
      logger.debug('highMagZoomCamURL: "' + daq_utils.highMagZoomCamURL + '"')

    def initVideo3(self,frequency):
      self.captureLowMagZoom=cv2.VideoCapture(daq_utils.lowMagZoomCamURL)
      logger.debug('lowMagZoomCamURL: "' + daq_utils.lowMagZoomCamURL + '"')
            
    def createSampleTab(self):

        sampleTab= QtWidgets.QWidget()      
        splitter1 = QtWidgets.QSplitter(Qt.Horizontal)
        vBoxlayout= QtWidgets.QVBoxLayout()
        self.dewarTreeFrame = QFrame()
        vBoxDFlayout= QtWidgets.QVBoxLayout()
        self.selectedSampleRequest = {}
        self.selectedSampleID = ""
        self.dewarTree   = DewarTree(self)
        self.dewarTree.clicked[QModelIndex].connect(self.row_clicked)
        treeSelectBehavior = QtWidgets.QAbstractItemView.SelectItems
        treeSelectMode = QtWidgets.QAbstractItemView.ExtendedSelection
        self.dewarTree.setSelectionMode(treeSelectMode)
        self.dewarTree.setSelectionBehavior(treeSelectBehavior)
        hBoxRadioLayout1= QtWidgets.QHBoxLayout()   
        self.viewRadioGroup=QtWidgets.QButtonGroup()
        self.priorityViewRadio = QtWidgets.QRadioButton("PriorityView")
        self.priorityViewRadio.toggled.connect(functools.partial(self.dewarViewToggledCB,"priorityView"))
        self.viewRadioGroup.addButton(self.priorityViewRadio)
        self.dewarViewRadio = QtWidgets.QRadioButton("DewarView")
        self.dewarViewRadio.setChecked(True)        
        self.dewarViewRadio.toggled.connect(functools.partial(self.dewarViewToggledCB,"dewarView"))
        hBoxRadioLayout1.addWidget(self.dewarViewRadio)        
        hBoxRadioLayout1.addWidget(self.priorityViewRadio)
        self.viewRadioGroup.addButton(self.dewarViewRadio)
        vBoxDFlayout.addLayout(hBoxRadioLayout1)
        vBoxDFlayout.addWidget(self.dewarTree)
        queueSelectedButton = QtWidgets.QPushButton("Queue All Selected")        
        queueSelectedButton.clicked.connect(self.dewarTree.queueAllSelectedCB)
        deQueueSelectedButton = QtWidgets.QPushButton("deQueue All Selected")        
        deQueueSelectedButton.clicked.connect(self.dewarTree.deQueueAllSelectedCB)
        runQueueButton = QtWidgets.QPushButton("Collect Queue")
        runQueueButton.setStyleSheet("background-color: yellow")
        runQueueButton.clicked.connect(self.collectQueueCB)
        stopRunButton = QtWidgets.QPushButton("Stop Collection")
        stopRunButton.setStyleSheet("background-color: red")
        stopRunButton.clicked.connect(self.stopRunCB) #immediate stop everything
        puckToDewarButton = QtWidgets.QPushButton("Puck to Dewar...")        
        mountSampleButton = QtWidgets.QPushButton("Mount Sample")        
        mountSampleButton.clicked.connect(self.mountSampleCB)
        unmountSampleButton = QtWidgets.QPushButton("Unmount Sample")        
        unmountSampleButton.clicked.connect(self.unmountSampleCB)
        puckToDewarButton.clicked.connect(self.puckToDewarCB)
        removePuckButton = QtWidgets.QPushButton("Remove Puck...")        
        removePuckButton.clicked.connect(self.removePuckCB)
        expandAllButton = QtWidgets.QPushButton("Expand All")        
        expandAllButton.clicked.connect(self.dewarTree.expandAllCB)
        collapseAllButton = QtWidgets.QPushButton("Collapse All")        
        collapseAllButton.clicked.connect(self.dewarTree.collapseAllCB)
        self.pauseQueueButton = QtWidgets.QPushButton("Pause")
        self.pauseQueueButton.clicked.connect(self.stopQueueCB) 
        emptyQueueButton = QtWidgets.QPushButton("Empty Queue")
        emptyQueueButton.clicked.connect(functools.partial(self.dewarTree.deleteSelectedCB,1))
        warmupButton = QtWidgets.QPushButton("Warmup Gripper")        
        warmupButton.clicked.connect(self.warmupGripperCB)
        self.openShutterButton = QtWidgets.QPushButton("Open Photon Shutter")        
        self.openShutterButton.clicked.connect(self.openPhotonShutterCB)
        self.popUserScreen = QtWidgets.QPushButton("User Screen...")
        self.popUserScreen.clicked.connect(self.popUserScreenCB)
        self.closeShutterButton = QtWidgets.QPushButton("Close Photon Shutter")        
        self.closeShutterButton.clicked.connect(self.closePhotonShutterCB)
        hBoxTreeButtsLayout = QtWidgets.QHBoxLayout()
        vBoxTreeButtsLayoutLeft = QtWidgets.QVBoxLayout()
        vBoxTreeButtsLayoutRight = QtWidgets.QVBoxLayout()
        vBoxTreeButtsLayoutLeft.addWidget(runQueueButton)
        vBoxTreeButtsLayoutLeft.addWidget(mountSampleButton)
        vBoxTreeButtsLayoutLeft.addWidget(self.pauseQueueButton)
        vBoxTreeButtsLayoutLeft.addWidget(queueSelectedButton)
        vBoxTreeButtsLayoutLeft.addWidget(self.popUserScreen)        
        vBoxTreeButtsLayoutLeft.addWidget(warmupButton)        
        vBoxTreeButtsLayoutRight.addWidget(stopRunButton)
        vBoxTreeButtsLayoutRight.addWidget(unmountSampleButton)        
        vBoxTreeButtsLayoutRight.addWidget(self.closeShutterButton)
        vBoxTreeButtsLayoutRight.addWidget(deQueueSelectedButton)        
        vBoxTreeButtsLayoutRight.addWidget(emptyQueueButton)
        hBoxTreeButtsLayout.addLayout(vBoxTreeButtsLayoutLeft)
        hBoxTreeButtsLayout.addLayout(vBoxTreeButtsLayoutRight)
        vBoxDFlayout.addLayout(hBoxTreeButtsLayout)
        self.dewarTreeFrame.setLayout(vBoxDFlayout)
        splitter1.addWidget(self.dewarTreeFrame)
        splitter11 = QtWidgets.QSplitter(Qt.Horizontal)
        self.mainSetupFrame = QFrame()
        self.mainSetupFrame.setFixedHeight(890)
        vBoxMainSetup = QtWidgets.QVBoxLayout()
        self.mainToolBox = QtWidgets.QToolBox()
        self.mainToolBox.setMinimumWidth(750)
        self.mainColFrame = QFrame()
        vBoxMainColLayout= QtWidgets.QVBoxLayout()
        colParamsGB = QtWidgets.QGroupBox()
        colParamsGB.setTitle("Acquisition")
        vBoxColParams1 = QtWidgets.QVBoxLayout()
        hBoxColParams1 = QtWidgets.QHBoxLayout()
        colStartLabel = QtWidgets.QLabel('Oscillation Start:')
        colStartLabel.setFixedWidth(140)
        colStartLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.osc_start_ledit = QtWidgets.QLineEdit()
        self.osc_start_ledit.setFixedWidth(60)
        self.colEndLabel = QtWidgets.QLabel('Oscillation Range:')
        self.colEndLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.colEndLabel.setFixedWidth(140)
        self.osc_end_ledit = QtWidgets.QLineEdit()
        self.setGuiValues({'osc_end':"180.0"})
        self.osc_end_ledit.setFixedWidth(60)
        self.osc_end_ledit.textChanged[str].connect(functools.partial(self.totalExpChanged,"oscEnd"))        
        hBoxColParams1.addWidget(colStartLabel)
        hBoxColParams1.addWidget(self.osc_start_ledit)
        hBoxColParams1.addWidget(self.colEndLabel)
        hBoxColParams1.addWidget(self.osc_end_ledit)
        hBoxColParams2 = QtWidgets.QHBoxLayout()
        colRangeLabel = QtWidgets.QLabel('Oscillation Width:')
        colRangeLabel.setFixedWidth(140)
        colRangeLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.osc_range_ledit = QtWidgets.QLineEdit()
        self.osc_range_ledit.setFixedWidth(60)
        self.stillModeCheckBox = QCheckBox("Stills")
        self.stillModeCheckBox.setEnabled(False)
        if (self.stillModeStatePV.get()):
          self.stillModeCheckBox.setChecked(True)
          self.setGuiValues({'osc_range':"0.0"})
        else:
          self.stillModeCheckBox.setChecked(False)          
        colExptimeLabel = QtWidgets.QLabel('ExposureTime:')
        self.stillModeCheckBox.clicked.connect(self.stillModeUserPushCB)        
        self.osc_range_ledit.textChanged[str].connect(functools.partial(self.totalExpChanged,"oscRange"))
        colExptimeLabel.setFixedWidth(140)
        colExptimeLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.exp_time_ledit = QtWidgets.QLineEdit()
        self.exp_time_ledit.setFixedWidth(60)
        self.exp_time_ledit.textChanged[str].connect(self.totalExpChanged)                
        self.exp_time_ledit.setValidator(QtGui.QDoubleValidator(VALID_EXP_TIMES[daq_utils.beamline]['min'], VALID_EXP_TIMES[daq_utils.beamline]['max'], VALID_EXP_TIMES[daq_utils.beamline]['digits']))
        self.exp_time_ledit.textChanged.connect(self.checkEntryState)
        hBoxColParams2.addWidget(colRangeLabel)
        hBoxColParams2.addWidget(self.osc_range_ledit)

        hBoxColParams2.addWidget(colExptimeLabel)
        hBoxColParams2.addWidget(self.exp_time_ledit)
        hBoxColParams25 = QtWidgets.QHBoxLayout()
        hBoxColParams25.addWidget(self.stillModeCheckBox)                
        totalExptimeLabel = QtWidgets.QLabel('Total Exposure Time (s):')
        totalExptimeLabel.setFixedWidth(155)
        totalExptimeLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.totalExptime_ledit = QtWidgets.QLineEdit()        
        self.totalExptime_ledit.setReadOnly(True)
        self.totalExptime_ledit.setFrame(False)
        self.totalExptime_ledit.setFixedWidth(60)
        self.totalExptime_ledit.setValidator(QtGui.QDoubleValidator(VALID_TOTAL_EXP_TIMES[daq_utils.beamline]['min'],
            VALID_TOTAL_EXP_TIMES[daq_utils.beamline]['max'], VALID_TOTAL_EXP_TIMES[daq_utils.beamline]['digits']))
        self.totalExptime_ledit.textChanged.connect(self.checkEntryState)

        sampleLifetimeLabel = QtWidgets.QLabel('Estimated Sample Lifetime (s): ')        
        if (daq_utils.beamline == "amx"):                                      
          self.sampleLifetimeReadback = QtEpicsPVLabel(daq_utils.pvLookupDict["sampleLifetime"],self,70,2)
          self.sampleLifetimeReadback_ledit = self.sampleLifetimeReadback.getEntry()
        else:
          calcLifetimeButton = QtWidgets.QPushButton("Calc. Lifetime")
          calcLifetimeButton.clicked.connect(self.calcLifetimeCB)
          self.sampleLifetimeReadback_ledit = QtWidgets.QLabel()
          self.calcLifetimeCB()
        hBoxColParams25.addWidget(totalExptimeLabel)
        hBoxColParams25.addWidget(self.totalExptime_ledit)
        if (daq_utils.beamline == "fmx"):
          hBoxColParams25.addWidget(calcLifetimeButton)
        hBoxColParams25.addWidget(sampleLifetimeLabel)
        hBoxColParams25.addWidget(self.sampleLifetimeReadback_ledit)
        hBoxColParams22 = QtWidgets.QHBoxLayout()
        if (daq_utils.beamline == "fmx"):
          if (getBlConfig("attenType") == "RI"):
            self.transmissionReadback = QtEpicsPVLabel(daq_utils.pvLookupDict["RI_Atten_SP"],self,60,3)
            self.transmissionSetPoint = QtEpicsPVEntry(daq_utils.pvLookupDict["RI_Atten_SP"],self,60,3)
            colTransmissionLabel = QtWidgets.QLabel('Transmission (RI) (0.0-1.0):')            
          else:
            self.transmissionReadback = QtEpicsPVLabel(daq_utils.pvLookupDict["transmissionRBV"],self,60,3)
            self.transmissionSetPoint = QtEpicsPVEntry(daq_utils.pvLookupDict["transmissionSet"],self,60,3)
            colTransmissionLabel = QtWidgets.QLabel('Transmission (BCU) (0.0-1.0):')            
        else:
            self.transmissionReadback = QtEpicsPVLabel(daq_utils.pvLookupDict["transmissionRBV"],self,60,3)
            self.transmissionSetPoint = QtEpicsPVEntry(daq_utils.pvLookupDict["transmissionSet"],self,60,3)
            colTransmissionLabel = QtWidgets.QLabel('Transmission (0.0-1.0):')            
        self.transmissionReadback_ledit = self.transmissionReadback.getEntry()

        colTransmissionLabel.setAlignment(QtCore.Qt.AlignCenter) 
        colTransmissionLabel.setFixedWidth(190)
        
        transmisionSPLabel = QtWidgets.QLabel("SetPoint:")

        self.transmission_ledit = self.transmissionSetPoint.getEntry()
        self.setGuiValues({'transmission':getBlConfig("stdTrans")})
        self.transmission_ledit.returnPressed.connect(self.setTransCB)        
        setTransButton = QtWidgets.QPushButton("Set Trans")
        setTransButton.clicked.connect(self.setTransCB)
        beamsizeLabel = QtWidgets.QLabel("BeamSize:")        
        beamSizeOptionList = ["V0H0","V0H1","V1H0","V1H1"]
        self.beamsizeComboBox = QtWidgets.QComboBox(self)
        self.beamsizeComboBox.addItems(beamSizeOptionList)
        self.beamsizeComboBox.setCurrentIndex(int(self.beamSize_pv.get()))
        self.beamsizeComboBox.activated[str].connect(self.beamsizeComboActivatedCB)
        if (daq_utils.beamline == "amx" or self.energy_pv.get() < 9000):
          self.beamsizeComboBox.setEnabled(False)
        hBoxColParams3 = QtWidgets.QHBoxLayout()
        colEnergyLabel = QtWidgets.QLabel('Energy (eV):')
        colEnergyLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.energyMotorEntry = QtEpicsPVLabel(daq_utils.motor_dict["energy"]+ ".RBV",self,70,2)
        self.energyReadback = self.energyMotorEntry.getEntry()
        energySPLabel = QtWidgets.QLabel("SetPoint:")
        self.energyMoveLedit = QtEpicsPVEntry(daq_utils.motor_dict["energy"] + ".VAL",self,75,2)
        self.energy_ledit = self.energyMoveLedit.getEntry()
        self.energy_ledit.returnPressed.connect(self.moveEnergyCB)        
        moveEnergyButton = QtWidgets.QPushButton("Move Energy")
        moveEnergyButton.clicked.connect(self.moveEnergyCB)        
        hBoxColParams3.addWidget(colEnergyLabel)
        hBoxColParams3.addWidget(self.energyReadback)
        hBoxColParams3.addWidget(energySPLabel)        
        hBoxColParams3.addWidget(self.energy_ledit)
        hBoxColParams22.addWidget(colTransmissionLabel)
        hBoxColParams22.addWidget(self.transmissionReadback_ledit)
        hBoxColParams22.addWidget(transmisionSPLabel)
        hBoxColParams22.addWidget(self.transmission_ledit)
        hBoxColParams22.insertSpacing(5,100)
        hBoxColParams22.addWidget(beamsizeLabel)
        hBoxColParams22.addWidget(self.beamsizeComboBox)        
        hBoxColParams4 = QtWidgets.QHBoxLayout()
        colBeamWLabel = QtWidgets.QLabel('Beam Width:')
        colBeamWLabel.setFixedWidth(140)
        colBeamWLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.beamWidth_ledit = QtWidgets.QLineEdit()
        self.beamWidth_ledit.setFixedWidth(60)
        colBeamHLabel = QtWidgets.QLabel('Beam Height:')
        colBeamHLabel.setFixedWidth(140)
        colBeamHLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.beamHeight_ledit = QtWidgets.QLineEdit()
        self.beamHeight_ledit.setFixedWidth(60)
        hBoxColParams4.addWidget(colBeamWLabel)
        hBoxColParams4.addWidget(self.beamWidth_ledit)
        hBoxColParams4.addWidget(colBeamHLabel)
        hBoxColParams4.addWidget(self.beamHeight_ledit)
        hBoxColParams5 = QtWidgets.QHBoxLayout()
        colResoLabel = QtWidgets.QLabel('Edge Resolution:')
        colResoLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.resolution_ledit = QtWidgets.QLineEdit()
        self.resolution_ledit.setFixedWidth(60)
        self.resolution_ledit.textEdited[str].connect(self.resoTextChanged)
        detDistLabel = QtWidgets.QLabel('Detector Dist.')
        detDistLabel.setAlignment(QtCore.Qt.AlignCenter)         
        detDistRBLabel = QtWidgets.QLabel("Readback:")
        self.detDistRBVLabel = QtEpicsPVLabel(daq_utils.motor_dict["detectorDist"] + ".RBV",self,70) 
        detDistSPLabel = QtWidgets.QLabel("SetPoint:")
        self.detDistMotorEntry = QtEpicsPVEntry(daq_utils.motor_dict["detectorDist"] + ".VAL",self,70,2)
        self.detDistMotorEntry.getEntry().setValidator(QtGui.QDoubleValidator(VALID_DET_DIST[daq_utils.beamline]['min'],
            VALID_DET_DIST[daq_utils.beamline]['max'], VALID_DET_DIST[daq_utils.beamline]['digits']))
        self.detDistMotorEntry.getEntry().textChanged[str].connect(self.detDistTextChanged)
        self.detDistMotorEntry.getEntry().textChanged[str].connect(self.checkEntryState)
        self.detDistMotorEntry.getEntry().returnPressed.connect(self.moveDetDistCB)        
        self.moveDetDistButton = QtWidgets.QPushButton("Move Detector")
        self.moveDetDistButton.clicked.connect(self.moveDetDistCB)
        hBoxColParams3.addWidget(detDistLabel)
        hBoxColParams3.addWidget(self.detDistRBVLabel.getEntry())
        hBoxColParams3.addWidget(detDistSPLabel)        
        hBoxColParams3.addWidget(self.detDistMotorEntry.getEntry())
        hBoxColParams6 = QtWidgets.QHBoxLayout()
        hBoxColParams6.setAlignment(QtCore.Qt.AlignLeft) 
        hBoxColParams7 = QtWidgets.QHBoxLayout()
        hBoxColParams7.setAlignment(QtCore.Qt.AlignLeft) 
        centeringLabel = QtWidgets.QLabel('Sample Centering:')
        centeringLabel.setFixedWidth(140)        
        centeringOptionList = ["Interactive","AutoLoop","AutoRaster","Testing"]
        self.centeringComboBox = QtWidgets.QComboBox(self)
        self.centeringComboBox.addItems(centeringOptionList)
        protoLabel = QtWidgets.QLabel('Protocol:')
        font = QtGui.QFont()
        font.setBold(True)
        protoLabel.setFont(font)
        protoLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.protoRadioGroup=QtWidgets.QButtonGroup()
        self.protoStandardRadio = QtWidgets.QRadioButton("standard")
        self.protoStandardRadio.setChecked(True)
        self.protoStandardRadio.toggled.connect(functools.partial(self.protoRadioToggledCB,"standard"))
        self.protoStandardRadio.pressed.connect(functools.partial(self.protoRadioToggledCB,"standard"))        
        self.protoRadioGroup.addButton(self.protoStandardRadio)
        self.protoRasterRadio = QtWidgets.QRadioButton("raster")
        self.protoRasterRadio.toggled.connect(functools.partial(self.protoRadioToggledCB,"raster"))
        self.protoRasterRadio.pressed.connect(functools.partial(self.protoRadioToggledCB,"raster"))                
        self.protoRadioGroup.addButton(self.protoRasterRadio)
        self.protoVectorRadio = QtWidgets.QRadioButton("vector")
        self.protoRasterRadio.toggled.connect(functools.partial(self.protoRadioToggledCB,"vector"))
        self.protoRasterRadio.pressed.connect(functools.partial(self.protoRadioToggledCB,"vector"))        
        self.protoRadioGroup.addButton(self.protoVectorRadio)
        self.protoOtherRadio = QtWidgets.QRadioButton("other")
        self.protoOtherRadio.setEnabled(False)
        self.protoRadioGroup.addButton(self.protoOtherRadio)
        protoOptionList = ["standard","screen","raster","vector","burn","eScan","rasterScreen","stepRaster","stepVector","multiCol","characterize","ednaCol","specRaster"] # these should probably come from db
        self.protoComboBox = QtWidgets.QComboBox(self)
        self.protoComboBox.addItems(protoOptionList)
        self.protoComboBox.activated[str].connect(self.protoComboActivatedCB) 
        hBoxColParams6.addWidget(protoLabel)
        hBoxColParams6.addWidget(self.protoStandardRadio)
        hBoxColParams6.addWidget(self.protoRasterRadio)
        hBoxColParams6.addWidget(self.protoVectorRadio)        
        hBoxColParams6.addWidget(self.protoComboBox)
        hBoxColParams7.addWidget(centeringLabel)
        hBoxColParams7.addWidget(self.centeringComboBox)
        hBoxColParams7.addWidget(colResoLabel)
        hBoxColParams7.addWidget(self.resolution_ledit)
        self.processingOptionsFrame = QFrame()
        self.hBoxProcessingLayout1= QtWidgets.QHBoxLayout()        
        self.hBoxProcessingLayout1.setAlignment(QtCore.Qt.AlignLeft) 
        procOptionLabel = QtWidgets.QLabel('Processing Options:')
        procOptionLabel.setFixedWidth(200)
        self.autoProcessingCheckBox = QCheckBox("AutoProcessing On")
        self.autoProcessingCheckBox.setChecked(True)
        self.autoProcessingCheckBox.stateChanged.connect(self.autoProcessingCheckCB)
        self.fastDPCheckBox = QCheckBox("FastDP")
        self.fastDPCheckBox.setChecked(False)
        self.fastEPCheckBox = QCheckBox("FastEP")
        self.fastEPCheckBox.setChecked(False)
        self.fastEPCheckBox.setEnabled(False)
        self.dimpleCheckBox = QCheckBox("Dimple")
        self.dimpleCheckBox.setChecked(True)        
        self.xia2CheckBox = QCheckBox("Xia2")
        self.xia2CheckBox.setChecked(False)
        self.hBoxProcessingLayout1.addWidget(self.autoProcessingCheckBox)                
        self.hBoxProcessingLayout1.addWidget(self.fastDPCheckBox)
        self.hBoxProcessingLayout1.addWidget(self.fastEPCheckBox)
        self.hBoxProcessingLayout1.addWidget(self.dimpleCheckBox)                
        self.processingOptionsFrame.setLayout(self.hBoxProcessingLayout1)
        self.rasterParamsFrame = QFrame()
        self.vBoxRasterParams = QtWidgets.QVBoxLayout()
        self.hBoxRasterLayout1= QtWidgets.QHBoxLayout()        
        self.hBoxRasterLayout1.setAlignment(QtCore.Qt.AlignLeft) 
        self.hBoxRasterLayout2= QtWidgets.QHBoxLayout()        
        self.hBoxRasterLayout2.setAlignment(QtCore.Qt.AlignLeft) 
        rasterStepLabel = QtWidgets.QLabel('Raster Step')
        rasterStepLabel.setFixedWidth(110)
        self.rasterStepEdit = QtWidgets.QLineEdit(str(self.rasterStepDefs["Coarse"]))
        self.rasterStepEdit.textChanged[str].connect(self.rasterStepChanged)        
        self.rasterStepEdit.setFixedWidth(60)
        self.rasterGrainRadioGroup=QtWidgets.QButtonGroup()
        self.rasterGrainCoarseRadio = QtWidgets.QRadioButton("Coarse")
        self.rasterGrainCoarseRadio.setChecked(False)
        self.rasterGrainCoarseRadio.toggled.connect(functools.partial(self.rasterGrainToggledCB,"Coarse"))
        self.rasterGrainRadioGroup.addButton(self.rasterGrainCoarseRadio)
        self.rasterGrainFineRadio = QtWidgets.QRadioButton("Fine")
        self.rasterGrainFineRadio.setChecked(False)
        self.rasterGrainFineRadio.toggled.connect(functools.partial(self.rasterGrainToggledCB,"Fine"))
        self.rasterGrainRadioGroup.addButton(self.rasterGrainFineRadio)
        self.rasterGrainVFineRadio = QtWidgets.QRadioButton("VFine")
        self.rasterGrainVFineRadio.setChecked(False)
        self.rasterGrainVFineRadio.toggled.connect(functools.partial(self.rasterGrainToggledCB,"VFine"))
        self.rasterGrainRadioGroup.addButton(self.rasterGrainVFineRadio)
        self.rasterGrainCustomRadio = QtWidgets.QRadioButton("Custom")
        self.rasterGrainCustomRadio.setChecked(True)
        self.rasterGrainCustomRadio.toggled.connect(functools.partial(self.rasterGrainToggledCB,"Custom"))
        self.rasterGrainRadioGroup.addButton(self.rasterGrainCustomRadio)
        rasterEvalLabel = QtWidgets.QLabel('Raster\nEvaluate By:')
        rasterEvalOptionList = ["Spot Count","Resolution","Intensity"]
        self.rasterEvalComboBox = QtWidgets.QComboBox(self)
        self.rasterEvalComboBox.addItems(rasterEvalOptionList)
        self.rasterEvalComboBox.setCurrentIndex(db_lib.beamlineInfo(daq_utils.beamline,'rasterScoreFlag')["index"])
        self.rasterEvalComboBox.activated[str].connect(self.rasterEvalComboActivatedCB)
        self.hBoxRasterLayout1.addWidget(rasterStepLabel)
        self.hBoxRasterLayout1.addWidget(self.rasterStepEdit)
        self.hBoxRasterLayout1.addWidget(self.rasterGrainCoarseRadio)
        self.hBoxRasterLayout1.addWidget(self.rasterGrainFineRadio)
        self.hBoxRasterLayout1.addWidget(self.rasterGrainVFineRadio)        
        self.hBoxRasterLayout1.addWidget(self.rasterGrainCustomRadio)
        self.hBoxRasterLayout1.addWidget(rasterEvalLabel)
        self.hBoxRasterLayout1.addWidget(self.rasterEvalComboBox)
        self.vBoxRasterParams.addLayout(self.hBoxRasterLayout1)
        self.vBoxRasterParams.addLayout(self.hBoxRasterLayout2)        
        self.rasterParamsFrame.setLayout(self.vBoxRasterParams)
        self.multiColParamsFrame = QFrame() #something for criteria to decide on which hotspots to collect on for multi-xtal
        self.hBoxMultiColParamsLayout1 = QtWidgets.QHBoxLayout()
        self.hBoxMultiColParamsLayout1.setAlignment(QtCore.Qt.AlignLeft)
        multiColCutoffLabel = QtWidgets.QLabel('Diffraction Cutoff')
        multiColCutoffLabel.setFixedWidth(110)
        self.multiColCutoffEdit = QtWidgets.QLineEdit("320") #may need to store this in DB at some point, it's a silly number for now
        self.multiColCutoffEdit.setFixedWidth(60)
        self.hBoxMultiColParamsLayout1.addWidget(multiColCutoffLabel)
        self.hBoxMultiColParamsLayout1.addWidget(self.multiColCutoffEdit)
        self.multiColParamsFrame.setLayout(self.hBoxMultiColParamsLayout1)
        self.characterizeParamsFrame = QFrame()
        vBoxCharacterizeParams1 = QtWidgets.QVBoxLayout()
        self.hBoxCharacterizeLayout1= QtWidgets.QHBoxLayout() 
        self.characterizeTargetLabel = QtWidgets.QLabel('Characterization Targets')       
        characterizeResoLabel = QtWidgets.QLabel('Resolution')
        characterizeResoLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeResoEdit = QtWidgets.QLineEdit("3.0")
        characterizeISIGLabel = QtWidgets.QLabel('I/Sigma')
        characterizeISIGLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeISIGEdit = QtWidgets.QLineEdit("2.0")
        self.characterizeAnomCheckBox = QCheckBox("Anomolous")
        self.characterizeAnomCheckBox.setChecked(False)
        self.hBoxCharacterizeLayout2 = QtWidgets.QHBoxLayout() 
        characterizeCompletenessLabel = QtWidgets.QLabel('Completeness')
        characterizeCompletenessLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeCompletenessEdit = QtWidgets.QLineEdit("0.99")
        characterizeMultiplicityLabel = QtWidgets.QLabel('Multiplicity')
        characterizeMultiplicityLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeMultiplicityEdit = QtWidgets.QLineEdit("auto")
        characterizeDoseLimitLabel = QtWidgets.QLabel('Dose Limit')
        characterizeDoseLimitLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeDoseLimitEdit = QtWidgets.QLineEdit("100")
        characterizeSpaceGroupLabel = QtWidgets.QLabel('Space Group')
        characterizeSpaceGroupLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeSpaceGroupEdit = QtWidgets.QLineEdit("P1")
        self.hBoxCharacterizeLayout1.addWidget(characterizeResoLabel)
        self.hBoxCharacterizeLayout1.addWidget(self.characterizeResoEdit)
        self.hBoxCharacterizeLayout1.addWidget(characterizeISIGLabel)
        self.hBoxCharacterizeLayout1.addWidget(self.characterizeISIGEdit)
        self.hBoxCharacterizeLayout1.addWidget(characterizeSpaceGroupLabel)
        self.hBoxCharacterizeLayout1.addWidget(self.characterizeSpaceGroupEdit)                        
        self.hBoxCharacterizeLayout1.addWidget(self.characterizeAnomCheckBox)        
        self.hBoxCharacterizeLayout2.addWidget(characterizeCompletenessLabel)
        self.hBoxCharacterizeLayout2.addWidget(self.characterizeCompletenessEdit)
        self.hBoxCharacterizeLayout2.addWidget(characterizeMultiplicityLabel)
        self.hBoxCharacterizeLayout2.addWidget(self.characterizeMultiplicityEdit)
        self.hBoxCharacterizeLayout2.addWidget(characterizeDoseLimitLabel)
        self.hBoxCharacterizeLayout2.addWidget(self.characterizeDoseLimitEdit)
        vBoxCharacterizeParams1.addWidget(self.characterizeTargetLabel)
        vBoxCharacterizeParams1.addLayout(self.hBoxCharacterizeLayout1)
        vBoxCharacterizeParams1.addLayout(self.hBoxCharacterizeLayout2)
        self.characterizeParamsFrame.setLayout(vBoxCharacterizeParams1)
        self.vectorParamsFrame = QFrame()
        hBoxVectorLayout1= QtWidgets.QHBoxLayout() 
        setVectorStartButton = QtWidgets.QPushButton("Vector\nStart") 
        setVectorStartButton.clicked.connect(self.setVectorStartCB)
        setVectorEndButton = QtWidgets.QPushButton("Vector\nEnd") 
        setVectorEndButton.clicked.connect(self.setVectorEndCB)
        vectorFPPLabel = QtWidgets.QLabel("Number of Wedges")
        self.vectorFPP_ledit = QtWidgets.QLineEdit("1")
        vecLenLabel = QtWidgets.QLabel("    Length(microns):")
        self.vecLenLabelOutput = QtWidgets.QLabel("---")
        vecSpeedLabel = QtWidgets.QLabel("    Speed(microns/s):")
        self.vecSpeedLabelOutput = QtWidgets.QLabel("---")
        hBoxVectorLayout1.addWidget(setVectorStartButton)
        hBoxVectorLayout1.addWidget(setVectorEndButton)
        hBoxVectorLayout1.addWidget(vectorFPPLabel)
        hBoxVectorLayout1.addWidget(self.vectorFPP_ledit)
        hBoxVectorLayout1.addWidget(vecLenLabel)
        hBoxVectorLayout1.addWidget(self.vecLenLabelOutput)
        hBoxVectorLayout1.addWidget(vecSpeedLabel)
        hBoxVectorLayout1.addWidget(self.vecSpeedLabelOutput)                
        self.vectorParamsFrame.setLayout(hBoxVectorLayout1)
        vBoxColParams1.addLayout(hBoxColParams1)
        vBoxColParams1.addLayout(hBoxColParams2)
        vBoxColParams1.addLayout(hBoxColParams25)                
        vBoxColParams1.addLayout(hBoxColParams22)        
        vBoxColParams1.addLayout(hBoxColParams3)
        vBoxColParams1.addLayout(hBoxColParams7)
        vBoxColParams1.addLayout(hBoxColParams6)        
        vBoxColParams1.addWidget(self.rasterParamsFrame)
        vBoxColParams1.addWidget(self.multiColParamsFrame)
        vBoxColParams1.addWidget(self.vectorParamsFrame)
        vBoxColParams1.addWidget(self.characterizeParamsFrame)
        vBoxColParams1.addWidget(self.processingOptionsFrame)
        self.rasterParamsFrame.hide()
        self.multiColParamsFrame.hide()
        self.characterizeParamsFrame.hide()
        colParamsGB.setLayout(vBoxColParams1)
        self.dataPathGB = DataLocInfo(self)
        hBoxDisplayOptionLayout= QtWidgets.QHBoxLayout()        
        self.albulaDispCheckBox = QCheckBox("Display Data (Albula)")
        self.albulaDispCheckBox.setChecked(False)
        hBoxDisplayOptionLayout.addWidget(self.albulaDispCheckBox)
        vBoxMainColLayout.addWidget(colParamsGB)
        vBoxMainColLayout.addWidget(self.dataPathGB)
        vBoxMainColLayout.addLayout(hBoxDisplayOptionLayout)
        self.mainColFrame.setLayout(vBoxMainColLayout)
        self.mainToolBox.addItem(self.mainColFrame,"Collection Parameters")        
        editSampleButton = QtWidgets.QPushButton("Apply Changes") 
        editSampleButton.clicked.connect(self.editSelectedRequestsCB)
        cloneRequestButton = QtWidgets.QPushButton("Clone Raster Request") 
        cloneRequestButton.clicked.connect(self.cloneRequestCB)
        hBoxPriorityLayout1= QtWidgets.QHBoxLayout()        
        priorityEditLabel = QtWidgets.QLabel("Priority Edit")
        priorityTopButton =  QtWidgets.QPushButton("   >>   ")
        priorityUpButton =   QtWidgets.QPushButton("   >    ")
        priorityDownButton = QtWidgets.QPushButton("   <    ")
        priorityBottomButton=QtWidgets.QPushButton("   <<   ")
        priorityTopButton.clicked.connect(self.topPriorityCB)
        priorityBottomButton.clicked.connect(self.bottomPriorityCB)
        priorityUpButton.clicked.connect(self.upPriorityCB)
        priorityDownButton.clicked.connect(self.downPriorityCB)
        hBoxPriorityLayout1.addWidget(priorityEditLabel)
        hBoxPriorityLayout1.addWidget(priorityBottomButton)
        hBoxPriorityLayout1.addWidget(priorityDownButton)
        hBoxPriorityLayout1.addWidget(priorityUpButton)
        hBoxPriorityLayout1.addWidget(priorityTopButton)
        queueSampleButton = QtWidgets.QPushButton("Add Requests to Queue") 
        queueSampleButton.clicked.connect(self.addRequestsToAllSelectedCB)
        deleteSampleButton = QtWidgets.QPushButton("Delete Requests") 
        deleteSampleButton.clicked.connect(functools.partial(self.dewarTree.deleteSelectedCB,0))
        editScreenParamsButton = QtWidgets.QPushButton("Edit Raster Params...") 
        editScreenParamsButton.clicked.connect(self.editScreenParamsCB)
        vBoxMainSetup.addWidget(self.mainToolBox)
        vBoxMainSetup.addLayout(hBoxPriorityLayout1)
        vBoxMainSetup.addWidget(queueSampleButton)
        vBoxMainSetup.addWidget(editSampleButton)
        vBoxMainSetup.addWidget(cloneRequestButton)

        vBoxMainSetup.addWidget(editScreenParamsButton)
        self.mainSetupFrame.setLayout(vBoxMainSetup)
        self.VidFrame = QFrame()
        self.VidFrame.setFixedWidth(680)
        vBoxVidLayout= QtWidgets.QVBoxLayout()
        self.captureLowMag = None
        self.captureHighMag = None
        self.captureHighMagZoom = None          
        self.captureLowMagZoom = None          
        if (daq_utils.has_xtalview):
          if (self.zoom3FrameRatePV.get() != 0):          
            _thread.start_new_thread(self.initVideo2,(.25,)) #highMag
          if (self.zoom4FrameRatePV.get() != 0):            
            _thread.start_new_thread(self.initVideo4,(.25,))          #this sets up highMagDigiZoom
          if (self.zoom2FrameRatePV.get() != 0):            
            _thread.start_new_thread(self.initVideo3,(.25,))          #this sets up lowMagDigiZoom
          if (self.zoom1FrameRatePV.get() != 0):
            self.captureLowMag=cv2.VideoCapture(daq_utils.lowMagCamURL)
            logger.debug('lowMagCamURL: "' + daq_utils.lowMagCamURL + '"')
        time.sleep(5) # is this needed????
        self.capture = self.captureLowMag
        self.timerHutch = QTimer()
        self.timerHutch.timeout.connect(self.timerHutchRefresh)
        self.timerHutch.start(HUTCH_TIMER_DELAY)

        self.timerSample = QTimer()
        self.timerSample.timeout.connect(self.timerSampleRefresh)
        self.timerSample.start(0)
        self.centeringMarksList = []
        self.rasterList = []
        self.rasterDefList = []
        self.polyPointItems = []
        self.rasterPoly = None
        self.measureLine = None
        self.scene = QtWidgets.QGraphicsScene(0,0,640,512,self)
        hBoxHutchVidsLayout= QtWidgets.QHBoxLayout()
        self.sceneHutchCorner = QtWidgets.QGraphicsScene(0,0,320,180,self)
        self.sceneHutchTop = QtWidgets.QGraphicsScene(0,0,320,180,self)                        
        self.scene.keyPressEvent = self.sceneKey
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.viewHutchCorner = QtWidgets.QGraphicsView(self.sceneHutchCorner)
        self.viewHutchTop = QtWidgets.QGraphicsView(self.sceneHutchTop)                
        self.pixmap_item = QtWidgets.QGraphicsPixmapItem(None)
        self.scene.addItem(self.pixmap_item)
        self.pixmap_item_HutchCorner = QtWidgets.QGraphicsPixmapItem(None)
        self.sceneHutchCorner.addItem(self.pixmap_item_HutchCorner)
        self.pixmap_item_HutchTop = QtWidgets.QGraphicsPixmapItem(None)
        self.sceneHutchTop.addItem(self.pixmap_item_HutchTop)

        self.pixmap_item.mousePressEvent = self.pixelSelect
        centerMarkBrush = QtGui.QBrush(QtCore.Qt.blue)                
        centerMarkPen = QtGui.QPen(centerMarkBrush,2.0)
        self.centerMarker = QtWidgets.QGraphicsSimpleTextItem("+")
        self.centerMarker.setZValue(10.0)
        self.centerMarker.setBrush(centerMarkBrush)
        font = QtGui.QFont('DejaVu Sans Light', self.centerMarkerCharSize,weight=0)
        self.centerMarker.setFont(font)        
        self.scene.addItem(self.centerMarker)
        self.centerMarker.setPos(daq_utils.screenPixCenterX-self.centerMarkerCharOffsetX,daq_utils.screenPixCenterY-self.centerMarkerCharOffsetY)
        self.zoomRadioGroup=QtWidgets.QButtonGroup()
        self.zoom1Radio = QtWidgets.QRadioButton("Mag1")
        self.zoom1Radio.setChecked(True)
        self.zoom1Radio.toggled.connect(functools.partial(self.zoomLevelToggledCB,"Zoom1"))
        self.zoomRadioGroup.addButton(self.zoom1Radio)
        self.zoom2Radio = QtWidgets.QRadioButton("Mag2")
        self.zoom2Radio.toggled.connect(functools.partial(self.zoomLevelToggledCB,"Zoom2"))
        self.zoomRadioGroup.addButton(self.zoom2Radio)
        self.zoom3Radio = QtWidgets.QRadioButton("Mag3")
        self.zoom3Radio.toggled.connect(functools.partial(self.zoomLevelToggledCB,"Zoom3"))
        self.zoomRadioGroup.addButton(self.zoom3Radio)
        self.zoom4Radio = QtWidgets.QRadioButton("Mag4")
        self.zoom4Radio.toggled.connect(functools.partial(self.zoomLevelToggledCB,"Zoom4"))
        self.zoomRadioGroup.addButton(self.zoom4Radio)
        beamOverlayPen = QtGui.QPen(QtCore.Qt.red)
        self.tempBeamSizeXMicrons = 30
        self.tempBeamSizeYMicrons = 30        
        self.beamSizeXPixels = self.screenXmicrons2pixels(self.tempBeamSizeXMicrons)
        self.beamSizeYPixels = self.screenYmicrons2pixels(self.tempBeamSizeYMicrons)
        self.overlayPosOffsetX = self.centerMarkerCharOffsetX-1
        self.overlayPosOffsetY = self.centerMarkerCharOffsetY-1     
        self.beamSizeOverlay = QtWidgets.QGraphicsRectItem(self.centerMarker.x()-self.overlayPosOffsetX,self.centerMarker.y()-self.overlayPosOffsetY,self.beamSizeXPixels,self.beamSizeYPixels)
        self.beamSizeOverlay.setPen(beamOverlayPen)
        self.scene.addItem(self.beamSizeOverlay)
        self.beamSizeOverlay.setVisible(False)
        self.beamSizeOverlay.setRect(self.overlayPosOffsetX+self.centerMarker.x()-(self.beamSizeXPixels/2),self.overlayPosOffsetY+self.centerMarker.y()-(self.beamSizeYPixels/2),self.beamSizeXPixels,self.beamSizeYPixels)
        scaleBrush = QtGui.QBrush(QtCore.Qt.blue)        
        scalePen = QtGui.QPen(scaleBrush,2.0)
        scaleTextPen = QtGui.QPen(scaleBrush,1.0)
        self.imageScaleLineLen = 50
        self.imageScale = self.scene.addLine(10,daq_utils.screenPixY-30,10+self.imageScaleLineLen, daq_utils.screenPixY-30, scalePen)
        self.imageScaleText = self.scene.addSimpleText("50 microns",font=QtGui.QFont("Times", 13))        
        self.imageScaleText.setPen(scaleTextPen)
        self.imageScaleText.setPos(10,450)
        self.click_positions = []
        self.vectorStartFlag = 0
        hBoxHutchVidsLayout.addWidget(self.viewHutchTop)
        hBoxHutchVidsLayout.addWidget(self.viewHutchCorner)        
        vBoxVidLayout.addLayout(hBoxHutchVidsLayout)
        vBoxVidLayout.addWidget(self.view)        
        hBoxSampleOrientationLayout = QtWidgets.QHBoxLayout()
        setDC2CPButton = QtWidgets.QPushButton("SetStart")
        setDC2CPButton.clicked.connect(self.setDCStartCB)        
        omegaLabel = QtWidgets.QLabel("Omega:")
        omegaMonitorPV = str(getBlConfig("omegaMonitorPV"))
        self.sampleOmegaRBVLedit = QtEpicsPVLabel(daq_utils.motor_dict["omega"] + "." + omegaMonitorPV,self,70) 
        omegaSPLabel = QtWidgets.QLabel("SetPoint:")
        self.sampleOmegaMoveLedit = QtEpicsPVEntry(daq_utils.motor_dict["omega"] + ".VAL",self,70,2)
        self.sampleOmegaMoveLedit.getEntry().returnPressed.connect(self.moveOmegaCB)
        moveOmegaButton = QtWidgets.QPushButton("Move")
        moveOmegaButton.clicked.connect(self.moveOmegaCB)
        omegaTweakNegButtonFine = QtWidgets.QPushButton("-5")        
        omegaTweakNegButton = QtWidgets.QPushButton("<")
        omegaTweakNegButton.clicked.connect(self.omegaTweakNegCB)
        omegaTweakNegButtonFine.clicked.connect(functools.partial(self.omegaTweakCB,-5))
        self.omegaTweakVal_ledit = QtWidgets.QLineEdit()
        self.omegaTweakVal_ledit.setFixedWidth(60)
        self.omegaTweakVal_ledit.setText("90")
        omegaTweakPosButtonFine = QtWidgets.QPushButton("+5")        
        omegaTweakPosButton = QtWidgets.QPushButton(">")
        omegaTweakPosButton.clicked.connect(self.omegaTweakPosCB)
        omegaTweakPosButtonFine.clicked.connect(functools.partial(self.omegaTweakCB,5))
        hBoxSampleOrientationLayout.addWidget(setDC2CPButton)
        hBoxSampleOrientationLayout.addWidget(omegaLabel)
        hBoxSampleOrientationLayout.addWidget(self.sampleOmegaRBVLedit.getEntry())
        hBoxSampleOrientationLayout.addWidget(omegaSPLabel)
        hBoxSampleOrientationLayout.addWidget(self.sampleOmegaMoveLedit.getEntry())
        spacerItem = QtWidgets.QSpacerItem(100, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        hBoxSampleOrientationLayout.insertSpacing(6,100)
        hBoxSampleOrientationLayout.addWidget(omegaTweakNegButtonFine)
        hBoxSampleOrientationLayout.addWidget(omegaTweakNegButton)        
        hBoxSampleOrientationLayout.addWidget(self.omegaTweakVal_ledit)
        hBoxSampleOrientationLayout.addWidget(omegaTweakPosButton)
        hBoxSampleOrientationLayout.addWidget(omegaTweakPosButtonFine)        
        hBoxSampleOrientationLayout.addStretch(1)
        hBoxVidControlLayout = QtWidgets.QHBoxLayout()
        lightLevelLabel = QtWidgets.QLabel("Light")
        lightLevelLabel.setAlignment(QtCore.Qt.AlignRight|Qt.AlignVCenter)         
        sampleBrighterButton = QtWidgets.QPushButton("+")
        sampleBrighterButton.setFixedWidth(30)
        sampleBrighterButton.clicked.connect(self.lightUpCB)
        sampleDimmerButton = QtWidgets.QPushButton("-")
        sampleDimmerButton.setFixedWidth(30)
        sampleDimmerButton.clicked.connect(self.lightDimCB)
        focusLabel = QtWidgets.QLabel("Focus")
        focusLabel.setAlignment(QtCore.Qt.AlignRight|Qt.AlignVCenter)         
        focusPlusButton = QtWidgets.QPushButton("+")
        focusPlusButton.setFixedWidth(30)
        focusPlusButton.clicked.connect(functools.partial(self.focusTweakCB,5))        
        focusMinusButton = QtWidgets.QPushButton("-")
        focusMinusButton.setFixedWidth(30)
        focusMinusButton.clicked.connect(functools.partial(self.focusTweakCB,-5))
        annealButton = QtWidgets.QPushButton("Anneal")
        annealButton.clicked.connect(self.annealButtonCB)
        annealTimeLabel = QtWidgets.QLabel("Time")
        self.annealTime_ledit = QtWidgets.QLineEdit()
        self.annealTime_ledit.setFixedWidth(40)
        self.annealTime_ledit.setText("0.5")
        magLevelLabel = QtWidgets.QLabel("Vid:")
        snapshotButton = QtWidgets.QPushButton("SnapShot")        
        snapshotButton.clicked.connect(self.saveVidSnapshotButtonCB)
        self.hideRastersCheckBox = QCheckBox("Hide\nRasters")
        self.hideRastersCheckBox.setChecked(False)
        self.hideRastersCheckBox.stateChanged.connect(self.hideRastersCB)
        hBoxVidControlLayout.addWidget(self.zoom1Radio)
        hBoxVidControlLayout.addWidget(self.zoom2Radio)
        hBoxVidControlLayout.addWidget(self.zoom3Radio)
        hBoxVidControlLayout.addWidget(self.zoom4Radio)
        hBoxVidControlLayout.addWidget(focusLabel)
        hBoxVidControlLayout.addWidget(focusPlusButton)
        hBoxVidControlLayout.addWidget(focusMinusButton)                        
        hBoxVidControlLayout.addWidget(lightLevelLabel)
        hBoxVidControlLayout.addWidget(sampleBrighterButton)
        hBoxVidControlLayout.addWidget(sampleDimmerButton)
        hBoxVidControlLayout.addWidget(annealButton)
        hBoxVidControlLayout.addWidget(annealTimeLabel)
        hBoxVidControlLayout.addWidget(self.annealTime_ledit)        
        hBoxSampleAlignLayout = QtWidgets.QHBoxLayout()
        centerLoopButton = QtWidgets.QPushButton("Center\nLoop")
        centerLoopButton.clicked.connect(self.autoCenterLoopCB)
        measureButton = QtWidgets.QPushButton("Measure")
        measureButton.clicked.connect(self.measurePolyCB)
        loopShapeButton = QtWidgets.QPushButton("Add Raster\nto Queue")
        loopShapeButton.clicked.connect(self.drawInteractiveRasterCB)
        runRastersButton = QtWidgets.QPushButton("Run\nRaster")
        runRastersButton.clicked.connect(self.runRastersCB)
        clearGraphicsButton = QtWidgets.QPushButton("Clear")
        clearGraphicsButton.clicked.connect(self.eraseCB)
        self.click3Button = QtWidgets.QPushButton("3-Click\nCenter")
        self.click3Button.clicked.connect(self.center3LoopCB)
        self.threeClickCount = 0
        saveCenteringButton = QtWidgets.QPushButton("Save\nCenter")
        saveCenteringButton.clicked.connect(self.saveCenterCB)
        selectAllCenteringButton = QtWidgets.QPushButton("Select All\nCenterings")
        selectAllCenteringButton.clicked.connect(self.selectAllCenterCB)
        hBoxSampleAlignLayout.addWidget(centerLoopButton)
        hBoxSampleAlignLayout.addWidget(clearGraphicsButton)
        hBoxSampleAlignLayout.addWidget(saveCenteringButton)
        hBoxSampleAlignLayout.addWidget(selectAllCenteringButton)
        hBoxSampleAlignLayout.addWidget(self.click3Button)
        hBoxSampleAlignLayout.addWidget(snapshotButton)
        hBoxSampleAlignLayout.addWidget(self.hideRastersCheckBox)                        
        hBoxRadioLayout100= QtWidgets.QHBoxLayout()
        vidActionLabel = QtWidgets.QLabel("Video Click Mode:")        
        self.vidActionRadioGroup=QtWidgets.QButtonGroup()
        self.vidActionC2CRadio = QtWidgets.QRadioButton("C2C")
        self.vidActionC2CRadio.setChecked(True)
        self.vidActionC2CRadio.toggled.connect(self.vidActionToggledCB)
        self.vidActionRadioGroup.addButton(self.vidActionC2CRadio)        
        self.vidActionDefineCenterRadio = QtWidgets.QRadioButton("Define Center")
        self.vidActionDefineCenterRadio.setChecked(False)
        self.vidActionDefineCenterRadio.setEnabled(False)        
        self.vidActionDefineCenterRadio.toggled.connect(self.vidActionToggledCB)
        self.vidActionRadioGroup.addButton(self.vidActionDefineCenterRadio)
        self.vidActionRasterExploreRadio = QtWidgets.QRadioButton("Raster Explore")
        self.vidActionRasterExploreRadio.setChecked(False)
        self.vidActionRasterExploreRadio.toggled.connect(self.vidActionToggledCB)
        self.vidActionRadioGroup.addButton(self.vidActionRasterExploreRadio)
        self.vidActionRasterSelectRadio = QtWidgets.QRadioButton("Raster Select")
        self.vidActionRasterSelectRadio.setChecked(False)
        self.vidActionRasterSelectRadio.toggled.connect(self.vidActionToggledCB)
        self.vidActionRasterDefRadio = QtWidgets.QRadioButton("Define Raster")
        self.vidActionRasterDefRadio.setChecked(False)
        self.vidActionRasterDefRadio.setEnabled(False)
        self.vidActionRasterDefRadio.toggled.connect(self.vidActionToggledCB)
        self.vidActionRadioGroup.addButton(self.vidActionRasterDefRadio)
        hBoxRadioLayout100.addWidget(vidActionLabel)
        hBoxRadioLayout100.addWidget(self.vidActionC2CRadio)
        hBoxRadioLayout100.addWidget(self.vidActionRasterExploreRadio)
        hBoxRadioLayout100.addWidget(self.vidActionRasterDefRadio)
        hBoxRadioLayout100.addWidget(self.vidActionDefineCenterRadio)                
        vBoxVidLayout.addLayout(hBoxSampleOrientationLayout)
        vBoxVidLayout.addLayout(hBoxVidControlLayout)
        vBoxVidLayout.addLayout(hBoxSampleAlignLayout)
        vBoxVidLayout.addLayout(hBoxRadioLayout100)
        self.VidFrame.setLayout(vBoxVidLayout)
        splitter11.addWidget(self.mainSetupFrame)
        self.colTabs= QtWidgets.QTabWidget()        
        self.energyFrame = QFrame()
        vBoxEScanFull = QtWidgets.QVBoxLayout()
        hBoxEScan = QtWidgets.QHBoxLayout()
        vBoxEScan = QtWidgets.QVBoxLayout()
        self.periodicTable = QPeriodicTable(butSize=20)
        self.periodicTable.elementClicked("Se")
        vBoxEScan.addWidget(self.periodicTable)
        self.EScanDataPathGB = DataLocInfo(self)
        vBoxEScan.addWidget(self.EScanDataPathGB)
        hBoxEScanParams = QtWidgets.QHBoxLayout()
        hBoxEScanButtons = QtWidgets.QHBoxLayout()                        
        tempPlotButton = QtWidgets.QPushButton("Queue Requests")        
        tempPlotButton.clicked.connect(self.queueEnScanCB)
        clearEnscanPlotButton = QtWidgets.QPushButton("Clear")        
        clearEnscanPlotButton.clicked.connect(self.clearEnScanPlotCB)        
        hBoxEScanButtons.addWidget(clearEnscanPlotButton)
        hBoxEScanButtons.addWidget(tempPlotButton)
        escanStepsLabel = QtWidgets.QLabel("Steps")        
        self.escan_steps_ledit = QtWidgets.QLineEdit()
        self.escan_steps_ledit.setText("41")
        escanStepsizeLabel = QtWidgets.QLabel("Stepsize (EVs)")        
        self.escan_stepsize_ledit = QtWidgets.QLineEdit()
        self.escan_stepsize_ledit.setText("1")
        hBoxEScanParams.addWidget(escanStepsLabel)
        hBoxEScanParams.addWidget(self.escan_steps_ledit)
        hBoxEScanParams.addWidget(escanStepsizeLabel)
        hBoxEScanParams.addWidget(self.escan_stepsize_ledit)
        hBoxChoochResults = QtWidgets.QHBoxLayout()
        hBoxChoochResults2 = QtWidgets.QHBoxLayout()        
        choochResultsLabel = QtWidgets.QLabel("Chooch Results")
        choochInflLabel = QtWidgets.QLabel("Infl")
        self.choochInfl = QtWidgets.QLabel("")
        self.choochInfl.setFixedWidth(70)                
        choochPeakLabel = QtWidgets.QLabel("Peak")
        self.choochPeak = QtWidgets.QLabel("")
        self.choochPeak.setFixedWidth(70)
        choochInflFPrimeLabel = QtWidgets.QLabel("fPrimeInfl")
        self.choochFPrimeInfl = QtWidgets.QLabel("")
        self.choochFPrimeInfl.setFixedWidth(70)                
        choochInflF2PrimeLabel = QtWidgets.QLabel("f2PrimeInfl")
        self.choochF2PrimeInfl = QtWidgets.QLabel("")
        self.choochF2PrimeInfl.setFixedWidth(70)                
        choochPeakFPrimeLabel = QtWidgets.QLabel("fPrimePeak")
        self.choochFPrimePeak = QtWidgets.QLabel("")
        self.choochFPrimePeak.setFixedWidth(70)                
        choochPeakF2PrimeLabel = QtWidgets.QLabel("f2PrimePeak")
        self.choochF2PrimePeak = QtWidgets.QLabel("")
        self.choochF2PrimePeak.setFixedWidth(70)                
        hBoxChoochResults.addWidget(choochResultsLabel)
        hBoxChoochResults.addWidget(choochInflLabel)
        hBoxChoochResults.addWidget(self.choochInfl)        
        hBoxChoochResults.addWidget(choochPeakLabel)
        hBoxChoochResults.addWidget(self.choochPeak)        
        hBoxChoochResults2.addWidget(choochInflFPrimeLabel)
        hBoxChoochResults2.addWidget(self.choochFPrimeInfl)
        hBoxChoochResults2.addWidget(choochInflF2PrimeLabel)                
        hBoxChoochResults2.addWidget(self.choochF2PrimeInfl)        
        hBoxChoochResults2.addWidget(choochPeakFPrimeLabel)
        hBoxChoochResults2.addWidget(self.choochFPrimePeak)
        hBoxChoochResults2.addWidget(choochPeakF2PrimeLabel)                
        hBoxChoochResults2.addWidget(self.choochF2PrimePeak)        
        vBoxEScan.addLayout(hBoxEScanParams)
        vBoxEScan.addLayout(hBoxEScanButtons)
        vBoxEScan.addLayout(hBoxChoochResults)
        vBoxEScan.addLayout(hBoxChoochResults2)        
        hBoxEScan.addLayout(vBoxEScan)
        verticalLine = QFrame()
        verticalLine.setFrameStyle(QFrame.VLine)
        self.EScanGraph = ScanWindow(self.energyFrame)
        hBoxEScan.addWidget(verticalLine)
        hBoxEScan.addWidget(self.EScanGraph)
        vBoxEScanFull.addLayout(hBoxEScan)
        self.choochGraph = ScanWindow(self.energyFrame) #TODO should be another type? need to be able to add curves
        vBoxEScanFull.addWidget(self.choochGraph)
        self.energyFrame.setLayout(vBoxEScanFull)
        splitter11.addWidget(self.VidFrame)
        self.colTabs.addTab(splitter11,"Sample Control")
        self.colTabs.addTab(self.energyFrame,"Energy Scan")
        splitter1.addWidget(self.colTabs)
        vBoxlayout.addWidget(splitter1)
        self.lastFileLabel2 = QtWidgets.QLabel('File:')
        self.lastFileLabel2.setFixedWidth(60)
        if (daq_utils.beamline == "amx"):                    
          self.lastFileRBV2 = QtEpicsPVLabel("XF:17IDB-ES:AMX{Det:Eig9M}cam1:FullFileName_RBV",self,0)            
        else:
          self.lastFileRBV2 = QtEpicsPVLabel("XF:17IDC-ES:FMX{Det:Eig16M}cam1:FullFileName_RBV",self,0)            
        fileHBoxLayout = QtWidgets.QHBoxLayout()
        fileHBoxLayout2 = QtWidgets.QHBoxLayout()        
        self.controlMasterCheckBox = QCheckBox("Control Master")
        self.controlMasterCheckBox.stateChanged.connect(self.changeControlMasterCB)
        self.controlMasterCheckBox.setChecked(False)
        fileHBoxLayout.addWidget(self.controlMasterCheckBox)        
        self.statusLabel = QtEpicsPVLabel(daq_utils.beamlineComm+"program_state",self,150,highlight_on_change=False)
        fileHBoxLayout.addWidget(self.statusLabel.getEntry())
        self.shutterStateLabel = QtWidgets.QLabel('Shutter State:')
        governorMessageLabel = QtWidgets.QLabel('Governor Message:')
        self.governorMessage = QtEpicsPVLabel(daq_utils.pvLookupDict["governorMessage"],self,140,highlight_on_change=False)
        ringCurrentMessageLabel = QtWidgets.QLabel('Ring(mA):')
        self.ringCurrentMessage = QtWidgets.QLabel(str(self.ringCurrent_pv.get()))
        beamAvailable = self.beamAvailable_pv.get()
        if (beamAvailable):
          self.beamAvailLabel = QtWidgets.QLabel("Beam Available")
          self.beamAvailLabel.setStyleSheet("background-color: #99FF66;")                  
        else:
          self.beamAvailLabel = QtWidgets.QLabel("No Beam")
          self.beamAvailLabel.setStyleSheet("background-color: red;")                  
        sampleExposed = self.sampleExposed_pv.get()
        if (sampleExposed):
          self.sampleExposedLabel = QtWidgets.QLabel("Sample Exposed")
          self.sampleExposedLabel.setStyleSheet("background-color: red;")                  
        else:
          self.sampleExposedLabel = QtWidgets.QLabel("Sample Not Exposed")
          self.sampleExposedLabel.setStyleSheet("background-color: #99FF66;")              
        gripperLabel = QtWidgets.QLabel('Gripper Temp:')
        self.gripperTempLabel = QtWidgets.QLabel('%.1f' % self.gripTemp_pv.get())
        cryostreamLabel = QtWidgets.QLabel('Cryostream Temp:')
        self.cryostreamTempLabel = QtWidgets.QLabel(str(self.cryostreamTemp_pv.get()))

        fileHBoxLayout.addWidget(gripperLabel)
        fileHBoxLayout.addWidget(self.gripperTempLabel)
        fileHBoxLayout.addWidget(cryostreamLabel)
        fileHBoxLayout.addWidget(self.cryostreamTempLabel)
        fileHBoxLayout.addWidget(ringCurrentMessageLabel)
        fileHBoxLayout.addWidget(self.ringCurrentMessage)
        fileHBoxLayout.addWidget(self.beamAvailLabel)
        fileHBoxLayout.addWidget(self.sampleExposedLabel)          
        fileHBoxLayout.addWidget(governorMessageLabel)
        fileHBoxLayout.addWidget(self.governorMessage.getEntry())
        fileHBoxLayout2.addWidget(self.lastFileLabel2)
        fileHBoxLayout2.addWidget(self.lastFileRBV2.getEntry())
        vBoxlayout.addLayout(fileHBoxLayout)
        vBoxlayout.addLayout(fileHBoxLayout2)        
        sampleTab.setLayout(vBoxlayout)   
        self.XRFTab = QtWidgets.QFrame()        
        XRFhBox = QtWidgets.QHBoxLayout()
        self.mcafit = McaAdvancedFit(self.XRFTab)
        XRFhBox.addWidget(self.mcafit)
        self.XRFTab.setLayout(XRFhBox)
        self.tabs.addTab(sampleTab,"Collect")
#12/19 - uncomment this to expose the PyMCA XRF interface. It's not connected to anything.        
        self.tabs.addTab(self.XRFTab,"XRF Spectrum")
        self.zoomLevelToggledCB("Zoom1")        

    def albulaCheckCB(self,state):
      if state != QtCore.Qt.Checked:
        albulaUtils.albulaClose()
      else:
        albulaUtils.albulaOpen() #TODO there is no albulaOpen method! remove?

    def annealButtonCB(self):
      try:
        ftime=float(self.annealTime_ledit.text())
        if (ftime >= 0.1 and ftime <= 5.0):
          comm_s = "anneal(" + str(ftime) + ")"
          logger.info(comm_s)
          self.send_to_server(comm_s)
        else:
          self.popupServerMessage("Anneal time must be between 0.1 and 5.0 seconds.")        
      except:
        pass
      

    def hideRastersCB(self,state):
      if state == QtCore.Qt.Checked:
        self.eraseRastersCB()
      else:
        self.refreshCollectionParams(self.selectedSampleRequest)          

    def stillModeUserPushCB(self,state):
      logger.info("still checkbox state " + str(state))
      if (self.controlEnabled()):
        if (state):
          self.stillMode_pv.put(1)
          self.setGuiValues({'osc_range':"0.0"})
        else:
          self.standardMode_pv.put(1)
      else:
        self.popupServerMessage("You don't have control")
        if (self.stillModeStatePV.get()):
          self.stillModeCheckBox.setChecked(True)
        else:
          self.stillModeCheckBox.setChecked(False)          
        
      
    
    def autoProcessingCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        self.fastDPCheckBox.setEnabled(True)
        self.dimpleCheckBox.setEnabled(True)
        self.xia2CheckBox.setEnabled(True)                                                          
      else:
        self.fastDPCheckBox.setEnabled(False)                                  
        self.fastEPCheckBox.setEnabled(False)
        self.dimpleCheckBox.setEnabled(False)
        self.xia2CheckBox.setEnabled(False)                                                          

        

    def rasterGrainToggledCB(self,identifier):
      if (identifier == "Coarse" or identifier == "Fine" or identifier == "VFine"):
        cellSize = self.rasterStepDefs[identifier]                  
        self.rasterStepEdit.setText(str(cellSize))
        self.beamWidth_ledit.setText(str(cellSize))
        self.beamHeight_ledit.setText(str(cellSize))          



    def vidActionToggledCB(self):
      if (len(self.rasterList) > 0):
        if (self.vidActionRasterSelectRadio.isChecked()):
          for i in range(len(self.rasterList)):
            if (self.rasterList[i] != None):
              self.rasterList[i]["graphicsItem"].setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)            
        else:
          for i in range(len(self.rasterList)):
            if (self.rasterList[i] != None):
              self.rasterList[i]["graphicsItem"].setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
              self.rasterList[i]["graphicsItem"].setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
      if (self.vidActionRasterDefRadio.isChecked()):
        self.click_positions = []
        self.showProtParams()
      if (self.vidActionC2CRadio.isChecked()):        
        self.click_positions = []
        if (self.protoComboBox.findText(str("raster")) == self.protoComboBox.currentIndex() or self.protoComboBox.findText(str("stepRaster")) == self.protoComboBox.currentIndex() or self.protoComboBox.findText(str("specRaster")) == self.protoComboBox.currentIndex()):
          self.protoComboBox.setCurrentIndex(self.protoComboBox.findText(str("standard")))
          self.protoComboActivatedCB("standard")          
        self.showProtParams()



    def adjustGraphics4ZoomChange(self,fov):
      imageScaleMicrons = int(round(self.imageScaleLineLen * (fov["x"]/daq_utils.screenPixX)))
      self.imageScaleText.setText(str(imageScaleMicrons) + " microns")
      if (self.rasterList != []):
        saveRasterList = self.rasterList
        self.eraseDisplayCB()
        for i in range(len(saveRasterList)):
          if (saveRasterList[i] == None): 
            self.rasterList.append(None)
          else:
            rasterXPixels = float(saveRasterList[i]["graphicsItem"].x())
            rasterYPixels = float(saveRasterList[i]["graphicsItem"].y())
            self.rasterXmicrons = rasterXPixels * (fov["x"]/daq_utils.screenPixX)
            self.rasterYmicrons = rasterYPixels * (fov["y"]/daq_utils.screenPixY)
            if (not self.hideRastersCheckBox.isChecked()):
              self.drawPolyRaster(db_lib.getRequestByID(saveRasterList[i]["uid"]),saveRasterList[i]["coords"]["x"],saveRasterList[i]["coords"]["y"],saveRasterList[i]["coords"]["z"])
              self.fillPolyRaster(db_lib.getRequestByID(saveRasterList[i]["uid"]))
            self.processSampMove(self.sampx_pv.get(),"x")
            self.processSampMove(self.sampy_pv.get(),"y")
            self.processSampMove(self.sampz_pv.get(),"z")
      if (self.vectorStart != None):
        self.processSampMove(self.sampx_pv.get(),"x")
        self.processSampMove(self.sampy_pv.get(),"y")
        self.processSampMove(self.sampz_pv.get(),"z")
      if (self.centeringMarksList != []):          
        self.processSampMove(self.sampx_pv.get(),"x")
        self.processSampMove(self.sampy_pv.get(),"y")
        self.processSampMove(self.sampz_pv.get(),"z")

    def flushBuffer(self,vidStream):
      if (vidStream == None):
        return
      for i in range (0,1000):
        stime = time.time()              
        vidStream.grab()
        etime = time.time()
        commTime = etime-stime
        if (commTime>.01):
          return

    
    def zoomLevelToggledCB(self,identifier):
      fov = {}
      zoomedCursorX = daq_utils.screenPixCenterX-self.centerMarkerCharOffsetX
      zoomedCursorY = daq_utils.screenPixCenterY-self.centerMarkerCharOffsetY
      if (self.zoom2Radio.isChecked()):
        self.flushBuffer(self.captureLowMagZoom)
        self.capture = self.captureLowMagZoom
        fov["x"] = daq_utils.lowMagFOVx/2.0
        fov["y"] = daq_utils.lowMagFOVy/2.0
        unzoomedCursorX = self.lowMagCursorX_pv.get()-self.centerMarkerCharOffsetX
        unzoomedCursorY = self.lowMagCursorY_pv.get()-self.centerMarkerCharOffsetY
        if (unzoomedCursorX*2.0<daq_utils.screenPixCenterX):
          zoomedCursorX = unzoomedCursorX*2.0
        if (unzoomedCursorY*2.0<daq_utils.screenPixCenterY):
          zoomedCursorY = unzoomedCursorY*2.0
        if (unzoomedCursorX-daq_utils.screenPixCenterX>daq_utils.screenPixCenterX/2):
          zoomedCursorX = (unzoomedCursorX*2.0) - daq_utils.screenPixX
        if (unzoomedCursorY-daq_utils.screenPixCenterY>daq_utils.screenPixCenterY/2):
          zoomedCursorY = (unzoomedCursorY*2.0) - daq_utils.screenPixY
        self.centerMarker.setPos(zoomedCursorX,zoomedCursorY)
        self.beamSizeXPixels = self.screenXmicrons2pixels(self.tempBeamSizeXMicrons)
        self.beamSizeYPixels = self.screenYmicrons2pixels(self.tempBeamSizeYMicrons)
        self.beamSizeOverlay.setRect(self.overlayPosOffsetX+self.centerMarker.x()-(self.beamSizeXPixels/2),self.overlayPosOffsetY+self.centerMarker.y()-(self.beamSizeYPixels/2),self.beamSizeXPixels,self.beamSizeYPixels)
      elif (self.zoom1Radio.isChecked()):
        self.flushBuffer(self.captureLowMag)
        self.capture = self.captureLowMag
        fov["x"] = daq_utils.lowMagFOVx
        fov["y"] = daq_utils.lowMagFOVy
        self.centerMarker.setPos(self.lowMagCursorX_pv.get()-self.centerMarkerCharOffsetX,self.lowMagCursorY_pv.get()-self.centerMarkerCharOffsetY)
        self.beamSizeXPixels = self.screenXmicrons2pixels(self.tempBeamSizeXMicrons)
        self.beamSizeYPixels = self.screenYmicrons2pixels(self.tempBeamSizeYMicrons)
        self.beamSizeOverlay.setRect(self.overlayPosOffsetX+self.centerMarker.x()-(self.beamSizeXPixels/2),self.overlayPosOffsetY+self.centerMarker.y()-(self.beamSizeYPixels/2),self.beamSizeXPixels,self.beamSizeYPixels)
      elif (self.zoom4Radio.isChecked()):
        self.flushBuffer(self.captureHighMagZoom)
        self.capture = self.captureHighMagZoom
        fov["x"] = daq_utils.highMagFOVx/2.0
        fov["y"] = daq_utils.highMagFOVy/2.0
        unzoomedCursorX = self.highMagCursorX_pv.get()-self.centerMarkerCharOffsetX
        unzoomedCursorY = self.highMagCursorY_pv.get()-self.centerMarkerCharOffsetY
        if (unzoomedCursorX*2.0<daq_utils.screenPixCenterX):
          zoomedCursorX = unzoomedCursorX*2.0
        if (unzoomedCursorY*2.0<daq_utils.screenPixCenterY):
          zoomedCursorY = unzoomedCursorY*2.0
        if (unzoomedCursorX-daq_utils.screenPixCenterX>daq_utils.screenPixCenterX/2):
          zoomedCursorX = (unzoomedCursorX*2.0) - daq_utils.screenPixX
        if (unzoomedCursorY-daq_utils.screenPixCenterY>daq_utils.screenPixCenterY/2):
          zoomedCursorY = (unzoomedCursorY*2.0) - daq_utils.screenPixY
        self.centerMarker.setPos(zoomedCursorX,zoomedCursorY)
        self.beamSizeXPixels = self.screenXmicrons2pixels(self.tempBeamSizeXMicrons)
        self.beamSizeYPixels = self.screenYmicrons2pixels(self.tempBeamSizeYMicrons)
        self.beamSizeOverlay.setRect(self.overlayPosOffsetX+self.centerMarker.x()-(self.beamSizeXPixels/2),self.overlayPosOffsetY+self.centerMarker.y()-(self.beamSizeYPixels/2),self.beamSizeXPixels,self.beamSizeYPixels)
      elif (self.zoom3Radio.isChecked()):
        self.flushBuffer(self.captureHighMag)
        self.capture = self.captureHighMag
        fov["x"] = daq_utils.highMagFOVx
        fov["y"] = daq_utils.highMagFOVy
        self.centerMarker.setPos(self.highMagCursorX_pv.get()-self.centerMarkerCharOffsetX,self.highMagCursorY_pv.get()-self.centerMarkerCharOffsetY)
        self.beamSizeXPixels = self.screenXmicrons2pixels(self.tempBeamSizeXMicrons)
        self.beamSizeYPixels = self.screenYmicrons2pixels(self.tempBeamSizeYMicrons)
        self.beamSizeOverlay.setRect(self.overlayPosOffsetX+self.centerMarker.x()-(self.beamSizeXPixels/2),self.overlayPosOffsetY+self.centerMarker.y()-(self.beamSizeYPixels/2),self.beamSizeXPixels,self.beamSizeYPixels)
      self.adjustGraphics4ZoomChange(fov)
      

    def saveVidSnapshotButtonCB(self): 
      comment,useOlog,ok = SnapCommentDialog.getComment()
      if (ok):
        self.saveVidSnapshotCB(comment,useOlog)


    def saveVidSnapshotCB(self,comment="",useOlog=False,reqID=None,rasterHeatJpeg=None):
      if (not os.path.exists("snapshots")):
        os.system("mkdir snapshots")
      width=640
      height=512
      targetrect = QRectF(0, 0, width, height)
      sourcerect = QRectF(0, 0, width, height)
      pix = QtGui.QPixmap(width, height)
      painter = QtGui.QPainter(pix)
      self.scene.render(painter, targetrect,sourcerect)
      painter.end()
      now = time.time()
      if (rasterHeatJpeg == None):
        if (reqID != None):
          filePrefix = db_lib.getRequestByID(reqID)["request_obj"]["file_prefix"]
          imagePath = os.getcwd()+"/snapshots/"+filePrefix+str(int(now))+".jpg"
        else:
          if (self.dataPathGB.prefix_ledit.text() != ""):            
            imagePath = os.getcwd()+"/snapshots/"+str(self.dataPathGB.prefix_ledit.text())+str(int(now))+".jpg"             
          else:
            imagePath = os.getcwd()+"/snapshots/capture"+str(int(now))+".jpg"
      else:
        imagePath = rasterHeatJpeg
      logger.info("saving " + imagePath)
      pix.save(imagePath, "JPG")
      if (useOlog):
        lsdcOlog.toOlogPicture(imagePath,str(comment))
      resultObj = {}
      imgRef = imagePath #for now, just the path, might want to use filestore later, if they really do facilitate moving files
      resultObj["data"] = imgRef
      resultObj["comment"] = str(comment)
      if (reqID != None): #assuming raster here, but will probably need to check the type
        db_lib.addResultforRequest("rasterJpeg",reqID,owner=daq_utils.owner,result_obj=resultObj,proposalID=daq_utils.getProposalID(),beamline=daq_utils.beamline)
      else: # the user pushed the snapshot button on the gui
        mountedSampleID = self.mountedPin_pv.get()
        if (mountedSampleID != ""): 
          db_lib.addResulttoSample("snapshotResult",mountedSampleID,owner=daq_utils.owner,result_obj=resultObj,proposalID=daq_utils.getProposalID(),beamline=daq_utils.beamline) 
        else: #beamline result, no sample mounted
          db_lib.addResulttoBL("snapshotResult",daq_utils.beamline,owner=daq_utils.owner,result_obj=resultObj,proposalID=daq_utils.getProposalID())        

      

    def changeControlMasterCB(self, state, processID=os.getpid()): #when someone touches checkbox, either through interaction or code
      logger.info("change control master")
      logger.info(processID)
      currentMaster = self.controlMaster_pv.get()
      if (currentMaster < 0):
        self.controlMaster_pv.put(currentMaster) #this makes sure if things are locked, and someone tries to get control, their checkbox will uncheck itself
        self.popupServerMessage("Control is locked by staff. Please stand by.")        
        return
      if (state == QtCore.Qt.Checked):
        self.controlMaster_pv.put(processID)
        if len(self.osc_range_ledit.text()) == 0 or abs(float(self.osc_range_ledit.text())) > 0:
          self.standardMode_pv.put(1)
        elif(float(self.osc_range_ledit.text()) == 0):
          self.stillMode_pv.put(1)
      else:
        self.userScreenDialog.hide()
        if (self.staffScreenDialog != None):
          self.staffScreenDialog.hide()

      

    def calculateNewYCoordPos(self,startYX,startYY):
      startY_pixels = 0
      zMotRBV = self.motPos["y"]
      yMotRBV = self.motPos["z"]
      if (self.scannerType == "PI"):                                  
        fineYRBV = self.motPos["fineY"]
        fineZRBV = self.motPos["fineZ"]      
        deltaYX = startYX-zMotRBV-fineZRBV
        deltaYY = startYY-yMotRBV-fineYRBV
      else:
        deltaYX = startYX-zMotRBV      
        deltaYY = startYY-yMotRBV
      omegaRad = math.radians(self.motPos["omega"])
      newYY = (float(startY_pixels-(self.screenYmicrons2pixels(deltaYY))))*math.sin(omegaRad)
      newYX = (float(startY_pixels-(self.screenYmicrons2pixels(deltaYX))))*math.cos(omegaRad)
      newY = newYX + newYY
      return newY


    def processROIChange(self,posRBV,ID):
      pass


    def processLowMagCursorChange(self,posRBV,ID):
      zoomedCursorX = daq_utils.screenPixCenterX-self.centerMarkerCharOffsetX
      zoomedCursorY = daq_utils.screenPixCenterY-self.centerMarkerCharOffsetY
      if (self.zoom2Radio.isChecked()):  #lowmagzoom
        unzoomedCursorX = self.lowMagCursorX_pv.get()-self.centerMarkerCharOffsetX
        unzoomedCursorY = self.lowMagCursorY_pv.get()-self.centerMarkerCharOffsetY
        if (unzoomedCursorX*2.0<daq_utils.screenPixCenterX):
          zoomedCursorX = unzoomedCursorX*2.0
        if (unzoomedCursorY*2.0<daq_utils.screenPixCenterY):
          zoomedCursorY = unzoomedCursorY*2.0
        if (unzoomedCursorX-daq_utils.screenPixCenterX>daq_utils.screenPixCenterX/2):
          zoomedCursorX = (unzoomedCursorX*2.0) - daq_utils.screenPixX
        if (unzoomedCursorY-daq_utils.screenPixCenterY>daq_utils.screenPixCenterY/2):           
          zoomedCursorY = (unzoomedCursorY*2.0) - daq_utils.screenPixY
        self.centerMarker.setPos(zoomedCursorX,zoomedCursorY)
        self.beamSizeXPixels = self.screenXmicrons2pixels(self.tempBeamSizeXMicrons)
        self.beamSizeYPixels = self.screenYmicrons2pixels(self.tempBeamSizeYMicrons)
        self.beamSizeOverlay.setRect(self.overlayPosOffsetX+self.centerMarker.x()-(self.beamSizeXPixels/2),self.overlayPosOffsetY+self.centerMarker.y()-(self.beamSizeYPixels/2),self.beamSizeXPixels,self.beamSizeYPixels)
      else:
        self.centerMarker.setPos(self.lowMagCursorX_pv.get()-self.centerMarkerCharOffsetX,self.lowMagCursorY_pv.get()-self.centerMarkerCharOffsetY)
        self.beamSizeXPixels = self.screenXmicrons2pixels(self.tempBeamSizeXMicrons)
        self.beamSizeYPixels = self.screenYmicrons2pixels(self.tempBeamSizeYMicrons)
        self.beamSizeOverlay.setRect(self.overlayPosOffsetX+self.centerMarker.x()-(self.beamSizeXPixels/2),self.overlayPosOffsetY+self.centerMarker.y()-(self.beamSizeYPixels/2),self.beamSizeXPixels,self.beamSizeYPixels)


    def processHighMagCursorChange(self,posRBV,ID):
      zoomedCursorX = daq_utils.screenPixCenterX-self.centerMarkerCharOffsetX
      zoomedCursorY = daq_utils.screenPixCenterY-self.centerMarkerCharOffsetY
      if (self.zoom4Radio.isChecked()):      #highmagzoom
        unzoomedCursorX = self.highMagCursorX_pv.get()-self.centerMarkerCharOffsetX
        unzoomedCursorY = self.highMagCursorY_pv.get()-self.centerMarkerCharOffsetY
        if (unzoomedCursorX*2.0<daq_utils.screenPixCenterX):
          zoomedCursorX = unzoomedCursorX*2.0
        if (unzoomedCursorY*2.0<daq_utils.screenPixCenterY):
          zoomedCursorY = unzoomedCursorY*2.0
        if (unzoomedCursorX-daq_utils.screenPixCenterX>daq_utils.screenPixCenterX/2):
          zoomedCursorX = (unzoomedCursorX*2.0) - daq_utils.screenPixX
        if (unzoomedCursorY-daq_utils.screenPixCenterY>daq_utils.screenPixCenterY/2):           
          zoomedCursorY = (unzoomedCursorY*2.0) - daq_utils.screenPixY
        self.centerMarker.setPos(zoomedCursorX,zoomedCursorY)
        self.beamSizeXPixels = self.screenXmicrons2pixels(self.tempBeamSizeXMicrons)
        self.beamSizeYPixels = self.screenYmicrons2pixels(self.tempBeamSizeYMicrons)
        self.beamSizeOverlay.setRect(self.overlayPosOffsetX+self.centerMarker.x()-(self.beamSizeXPixels/2),self.overlayPosOffsetY+self.centerMarker.y()-(self.beamSizeYPixels/2),self.beamSizeXPixels,self.beamSizeYPixels)
      else:
        self.centerMarker.setPos(self.highMagCursorX_pv.get()-self.centerMarkerCharOffsetX,self.highMagCursorY_pv.get()-self.centerMarkerCharOffsetY)
        self.beamSizeXPixels = self.screenXmicrons2pixels(self.tempBeamSizeXMicrons)
        self.beamSizeYPixels = self.screenYmicrons2pixels(self.tempBeamSizeYMicrons)
        self.beamSizeOverlay.setRect(self.overlayPosOffsetX+self.centerMarker.x()-(self.beamSizeXPixels/2),self.overlayPosOffsetY+self.centerMarker.y()-(self.beamSizeYPixels/2),self.beamSizeXPixels,self.beamSizeYPixels)

          
    def processSampMove(self,posRBV,motID):
#      print "new " + motID + " pos=" + str(posRBV)
      self.motPos[motID] = posRBV
      if (len(self.centeringMarksList)>0):
        for i in range(len(self.centeringMarksList)):
          if (self.centeringMarksList[i] != None):
            centerMarkerOffsetX = self.centeringMarksList[i]["centerCursorX"]-self.centerMarker.x()
            centerMarkerOffsetY = self.centeringMarksList[i]["centerCursorY"]-self.centerMarker.y()
            if (motID == "x"):
              startX = self.centeringMarksList[i]["sampCoords"]["x"]
              delta = startX-posRBV
              newX = float(self.screenXmicrons2pixels(delta))
              self.centeringMarksList[i]["graphicsItem"].setPos(newX-centerMarkerOffsetX,self.centeringMarksList[i]["graphicsItem"].y())
            if (motID == "y" or motID == "z" or motID == "omega"):
              startYY = self.centeringMarksList[i]["sampCoords"]["z"]
              startYX = self.centeringMarksList[i]["sampCoords"]["y"]
              newY = self.calculateNewYCoordPos(startYX,startYY)
              self.centeringMarksList[i]["graphicsItem"].setPos(self.centeringMarksList[i]["graphicsItem"].x(),newY-centerMarkerOffsetY)
      if (len(self.rasterList)>0):
        for i in range(len(self.rasterList)):
          if (self.rasterList[i] != None):
            if (motID == "x"):
              startX = self.rasterList[i]["coords"]["x"]
              delta = startX-posRBV
              newX = float(self.screenXmicrons2pixels(delta))
              self.rasterList[i]["graphicsItem"].setPos(newX,self.rasterList[i]["graphicsItem"].y())
            if (motID == "y" or motID == "z"):
              startYY = self.rasterList[i]["coords"]["z"]
              startYX = self.rasterList[i]["coords"]["y"]
              newY = self.calculateNewYCoordPos(startYX,startYY)
              self.rasterList[i]["graphicsItem"].setPos(self.rasterList[i]["graphicsItem"].x(),newY)

            if (motID == "fineX"):
              startX = self.rasterList[i]["coords"]["x"]
              delta = startX-posRBV-self.motPos["x"]
              newX = float(self.screenXmicrons2pixels(delta))
              self.rasterList[i]["graphicsItem"].setPos(newX,self.rasterList[i]["graphicsItem"].y())              
            if (motID == "fineY" or motID == "fineZ"):
              startYY = self.rasterList[i]["coords"]["z"]
              startYX = self.rasterList[i]["coords"]["y"]
              newY = self.calculateNewYCoordPos(startYX,startYY)
              self.rasterList[i]["graphicsItem"].setPos(self.rasterList[i]["graphicsItem"].x(),newY)
              
            if (motID == "omega"):
              if (abs(posRBV-self.rasterList[i]["coords"]["omega"])%360.0 > 5.0):                  
                self.rasterList[i]["graphicsItem"].setVisible(False)
              else:
                self.rasterList[i]["graphicsItem"].setVisible(True)                  
              startYY = self.rasterList[i]["coords"]["z"]
              startYX = self.rasterList[i]["coords"]["y"]
              newY = self.calculateNewYCoordPos(startYX,startYY)
              self.rasterList[i]["graphicsItem"].setPos(self.rasterList[i]["graphicsItem"].x(),newY)
            
      if (self.vectorStart != None):
        centerMarkerOffsetX = self.vectorStart["centerCursorX"]-self.centerMarker.x()
        centerMarkerOffsetY = self.vectorStart["centerCursorY"]-self.centerMarker.y()
          
        if (motID == "omega"):
          startYY = self.vectorStart["coords"]["z"]
          startYX = self.vectorStart["coords"]["y"]
          newY = self.calculateNewYCoordPos(startYX,startYY)
          self.vectorStart["graphicsitem"].setPos(self.vectorStart["graphicsitem"].x(),newY-centerMarkerOffsetY)
        if (motID == "x"):
          startX = self.vectorStart["coords"]["x"]
          delta = startX-posRBV
          newX = float(self.screenXmicrons2pixels(delta))
          self.vectorStart["graphicsitem"].setPos(newX-centerMarkerOffsetX,self.vectorStart["graphicsitem"].y())
        if (motID == "y" or motID == "z"):
          startYX = self.vectorStart["coords"]["y"]
          startYY = self.vectorStart["coords"]["z"]
          newY = self.calculateNewYCoordPos(startYX,startYY)
          self.vectorStart["graphicsitem"].setPos(self.vectorStart["graphicsitem"].x(),newY-centerMarkerOffsetY)
      if (self.vectorEnd != None):
        centerMarkerOffsetX = self.vectorEnd["centerCursorX"]-self.centerMarker.x()
        centerMarkerOffsetY = self.vectorEnd["centerCursorY"]-self.centerMarker.y()

        if (motID == "omega"):
          startYX = self.vectorEnd["coords"]["y"]
          startYY = self.vectorEnd["coords"]["z"]
          newY = self.calculateNewYCoordPos(startYX,startYY)
          self.vectorEnd["graphicsitem"].setPos(self.vectorEnd["graphicsitem"].x(),newY-centerMarkerOffsetY)
        if (motID == "x"):
          startX = self.vectorEnd["coords"]["x"]
          delta = startX-posRBV
          newX = float(self.screenXmicrons2pixels(delta))
          self.vectorEnd["graphicsitem"].setPos(newX-centerMarkerOffsetX,self.vectorEnd["graphicsitem"].y())
        if (motID == "y" or motID == "z"):
          startYX = self.vectorEnd["coords"]["y"]
          startYY = self.vectorEnd["coords"]["z"]
          newY = self.calculateNewYCoordPos(startYX,startYY)
          self.vectorEnd["graphicsitem"].setPos(self.vectorEnd["graphicsitem"].x(),newY-centerMarkerOffsetY)


      if (self.vectorStart != None and self.vectorEnd != None):
        self.vecLine.setLine(self.vectorStart["graphicsitem"].x()+self.vectorStart["centerCursorX"]+self.centerMarkerCharOffsetX,self.vectorStart["graphicsitem"].y()+self.vectorStart["centerCursorY"]+self.centerMarkerCharOffsetY,self.vectorEnd["graphicsitem"].x()+self.vectorStart["centerCursorX"]+self.centerMarkerCharOffsetX,self.vectorEnd["graphicsitem"].y()+self.vectorStart["centerCursorY"]+self.centerMarkerCharOffsetY)

    def queueEnScanCB(self):
      self.protoComboBox.setCurrentIndex(self.protoComboBox.findText(str("eScan")))      
      self.addRequestsToAllSelectedCB()
      self.treeChanged_pv.put(1)      

    def clearEnScanPlotCB(self):
      self.EScanGraph.removeCurves()     # get list of all curves to provide to method?
      self.choochGraph.removeCurves()

    def displayXrecRaster(self,xrecRasterFlag):
      self.xrecRasterFlag_pv.put("0")
      if (xrecRasterFlag=="100"):
        for i in range(len(self.rasterList)):
          if (self.rasterList[i] != None):
            self.scene.removeItem(self.rasterList[i]["graphicsItem"])
      else:
        logger.info("xrecrasterflag = %s" % xrecRasterFlag)
        try:
          rasterReq = db_lib.getRequestByID(xrecRasterFlag)
        except IndexError:
          logger.error('bad xrecRasterFlag: %s' % xrecRasterFlag)
          return
        rasterDef = rasterReq["request_obj"]["rasterDef"]
        if (rasterDef["status"] == RasterStatus.DRAWN.value):
          self.drawPolyRaster(rasterReq)
        elif (rasterDef["status"] == RasterStatus.READY_FOR_FILL.value):
          self.fillPolyRaster(
            rasterReq,
            waitTime=getBlConfig(RASTER_GUI_XREC_FILL_DELAY)
          )
          logger.info("polyraster filled by displayXrecRaster")
        elif (rasterDef["status"] == RasterStatus.READY_FOR_SNAPSHOT.value):
          if (self.controlEnabled()):          
            self.takeRasterSnapshot(rasterReq)
            logger.info("raster snapshot taken")
          self.vidActionRasterExploreRadio.setChecked(True)                    
          self.selectedSampleID = rasterReq["sample"]
          self.treeChanged_pv.put(1) #not sure about this
        elif (rasterDef["status"] == RasterStatus.READY_FOR_REPROCESS.value):
          self.fillPolyRaster(rasterReq)
          logger.info("reprocessed polyraster filled by displayXrecraster")
          if (self.controlEnabled()):
            self.takeRasterSnapshot(rasterReq)
            logger.info("reprocessed raster snapshot taken")  
          self.vidActionRasterExploreRadio.setChecked(True)                    
          self.selectedSampleID = rasterReq["sample"]
          self.treeChanged_pv.put(1) #not sure about this
        else:
          pass


    def processMountedPin(self,mountedPinPos):
      self.eraseCB()      
      self.treeChanged_pv.put(1)

    def processFastShutter(self,shutterVal):
      if (round(shutterVal)==round(self.fastShutterOpenPos_pv.get())):
        self.shutterStateLabel.setText("Shutter State:Open")
        self.shutterStateLabel.setStyleSheet("background-color: red;")        
      else:
        self.shutterStateLabel.setText("Shutter State:Closed")
        self.shutterStateLabel.setStyleSheet("background-color: #99FF66;")        

    def processGripTemp(self,gripVal):
      self.gripperTempLabel.setText('%.1f' % gripVal)
      if (int(gripVal) > -170):
        self.gripperTempLabel.setStyleSheet("background-color: red;")        
      else:
        self.gripperTempLabel.setStyleSheet("background-color: #99FF66;")        

    def processCryostreamTemp(self,cryostreamVal):
        self.cryostreamTempLabel.setText(str(cryostreamVal))

    def processRingCurrent(self,ringCurrentVal):
      self.ringCurrentMessage.setText(str(int(ringCurrentVal)))
      if (int(ringCurrentVal) < 390):
        self.ringCurrentMessage.setStyleSheet("background-color: red;")        
      else:
        self.ringCurrentMessage.setStyleSheet("background-color: #99FF66;")        
        
    def processBeamAvailable(self,beamAvailVal):
      if (int(beamAvailVal) == 1):
        self.beamAvailLabel.setText("Beam Available")
        self.beamAvailLabel.setStyleSheet("background-color: #99FF66;")        
      else:
        self.beamAvailLabel.setText("No Beam")        
        self.beamAvailLabel.setStyleSheet("background-color: red;")        

    def processSampleExposed(self,sampleExposedVal):
      if (int(sampleExposedVal) == 1):
        self.sampleExposedLabel.setText("Sample Exposed")
        self.sampleExposedLabel.setStyleSheet("background-color: red;")        
      else:
        self.sampleExposedLabel.setText("Sample Not Exposed")        
        self.sampleExposedLabel.setStyleSheet("background-color: #99FF66;")        
        
        
    def processBeamSize(self,beamSizeFlag):
      self.beamsizeComboBox.setCurrentIndex(beamSizeFlag)

    def processEnergyChange(self,energyVal):
      if (energyVal<9000):
        self.beamsizeComboBox.setEnabled(False)
      else:
        self.beamsizeComboBox.setEnabled(True)
        
    def processControlMaster(self,controlPID):
      logger.info("in callback controlPID = " + str(controlPID))
      if (abs(int(controlPID)) == self.processID):
        self.controlMasterCheckBox.setChecked(True)
      else:
        self.controlMasterCheckBox.setChecked(False)      

    def processZebraArmState(self,state):
      if (int(state)):
        self.userScreenDialog.zebraArmCheckBox.setChecked(True)
      else:
        self.userScreenDialog.zebraArmCheckBox.setChecked(False)          

    def processGovRobotSeReach(self,state):
      if (int(state)):
        self.userScreenDialog.SEbutton.setEnabled(True)
      else:
        self.userScreenDialog.SEbutton.setEnabled(False)

    def processGovRobotSaReach(self,state):
      if (int(state)):
        self.userScreenDialog.SAbutton.setEnabled(True)
      else:
        self.userScreenDialog.SAbutton.setEnabled(False)
        
    def processGovRobotDaReach(self,state):
      if (int(state)):
        self.userScreenDialog.DAbutton.setEnabled(True)
      else:
        self.userScreenDialog.DAbutton.setEnabled(False)
        
    def processGovRobotBlReach(self,state):
      if (int(state)):
        self.userScreenDialog.BLbutton.setEnabled(True)
      else:
        self.userScreenDialog.BLbutton.setEnabled(False)
                

    def processDetMessage(self,state):
      self.userScreenDialog.detMessage_ledit.setText(str(state))

    def processSampleFlux(self,state):
      self.userScreenDialog.sampleFluxLabel.setText('%E' % state)

        
    def processZebraPulseState(self,state):
      if (int(state)):
        self.userScreenDialog.zebraPulseCheckBox.setChecked(True)
      else:
        self.userScreenDialog.zebraPulseCheckBox.setChecked(False)          

    def processStillModeState(self,state):
      if (int(state)):
        self.stillModeCheckBox.setChecked(True)
      else:
        self.stillModeCheckBox.setChecked(False)          

    def processZebraDownloadState(self,state):
      if (int(state)):
        self.userScreenDialog.zebraDownloadCheckBox.setChecked(True)
      else:
        self.userScreenDialog.zebraDownloadCheckBox.setChecked(False)          
        
    def processZebraSentTriggerState(self,state):
      if (int(state)):
        self.userScreenDialog.zebraSentTriggerCheckBox.setChecked(True)
      else:
        self.userScreenDialog.zebraSentTriggerCheckBox.setChecked(False)          

    def processZebraReturnedTriggerState(self,state):
      if (int(state)):
        self.userScreenDialog.zebraReturnedTriggerCheckBox.setChecked(True)
      else:
        self.userScreenDialog.zebraReturnedTriggerCheckBox.setChecked(False)          
        

    def processControlMasterNew(self,controlPID):
      logger.info("in callback controlPID = " + str(controlPID))
      if (abs(int(controlPID)) != self.processID):
        self.controlMasterCheckBox.setChecked(False)      

    def processChoochResult(self,choochResultFlag):
      if (choochResultFlag == "0"):
        return
      choochResult = db_lib.getResult(choochResultFlag)
      choochResultObj = choochResult["result_obj"]
      graph_x = choochResultObj["choochInXAxis"]
      graph_y = choochResultObj["choochInYAxis"]
      self.EScanGraph.name = "Chooch PLot"
      try:
        self.EScanGraph.addCurve(graph_x, graph_y, 'Raw counts vs. energy')
        self.EScanGraph.replot()
      except TypeError as e:
        logger.error('Problems with data type going into energy scan plot: %s' % (e))
      chooch_graph_x = choochResultObj["choochOutXAxis"]
      chooch_graph_y1 = choochResultObj["choochOutY1Axis"]
      chooch_graph_y2 = choochResultObj["choochOutY2Axis"]      
      self.choochGraph.name = "Chooch PLot"
      try:
        self.choochGraph.addCurve(chooch_graph_x, chooch_graph_y1, legend='spline')
        self.choochGraph.addCurve(chooch_graph_x, chooch_graph_y2, legend='fp')
        self.choochGraph.replot()
        self.choochInfl.setText(str(choochResultObj["infl"]))
        self.choochPeak.setText(str(choochResultObj["peak"]))
        self.choochFPrimeInfl.setText(str(choochResultObj["fprime_infl"]))
        self.choochFPrimePeak.setText(str(choochResultObj["fprime_peak"]))
        self.choochF2PrimeInfl.setText(str(choochResultObj["f2prime_infl"]))
        self.choochF2PrimePeak.setText(str(choochResultObj["f2prime_peak"]))
        self.choochResultFlag_pv.put("0")
        self.protoComboBox.setCurrentIndex(self.protoComboBox.findText(str("standard")))
        self.protoComboActivatedCB("standard")
      except TypeError as e:
        logger.error('Chooch plotting failed - check whether scan had a strong signal or not: %s' % (e))
      


# seems like we should be able to do an aggregate query to mongo for max/min :(
    def getMaxPriority(self):
      orderedRequests = db_lib.getOrderedRequestList(daq_utils.beamline)      
      priorityMax = 0
      for i in range(len(orderedRequests)):
        if (orderedRequests[i]["priority"] > priorityMax):
          priorityMax = orderedRequests[i]["priority"]
      return priorityMax

    def getMinPriority(self):
      orderedRequests = db_lib.getOrderedRequestList(daq_utils.beamline)      
      priorityMin = 10000000
      for i in range(len(orderedRequests)):
        if ((orderedRequests[i]["priority"] < priorityMin) and orderedRequests[i]["priority"]>0):
          priorityMin = orderedRequests[i]["priority"]
      return priorityMin


    def showProtParams(self):
      protocol = str(self.protoComboBox.currentText())
      self.rasterParamsFrame.hide()
      self.characterizeParamsFrame.hide()
      self.processingOptionsFrame.hide()
      self.multiColParamsFrame.hide()
      self.osc_start_ledit.setEnabled(True)
      self.osc_end_ledit.setEnabled(True)
      if (protocol == "raster" or protocol == "rasterScreen"):
        self.rasterParamsFrame.show()
        self.osc_start_ledit.setEnabled(False)
        self.osc_end_ledit.setEnabled(False)
        
      elif (protocol == "stepRaster" or protocol == "specRaster"):
        self.rasterParamsFrame.show()
        self.processingOptionsFrame.show()        
      elif (protocol == "multiCol" or protocol == "multiColQ"):
        self.rasterParamsFrame.show()
        self.multiColParamsFrame.show()
      elif (protocol == "screen"):
        pass
      elif (protocol == "vector" or protocol == "stepVector"):
        self.vectorParamsFrame.show()
        self.processingOptionsFrame.show()        
      elif (protocol == "characterize" or protocol == "ednaCol"):
        self.characterizeParamsFrame.show()
        self.processingOptionsFrame.show()                
      elif (protocol == "standard" or protocol == "burn"):
        self.processingOptionsFrame.show()
      else:
        pass 

    def rasterStepChanged(self,text):
      self.beamWidth_ledit.setText(text)
      self.beamHeight_ledit.setText(text)


    def updateVectorLengthAndSpeed(self):
      x_vec_end = self.vectorEnd["coords"]["x"]
      y_vec_end = self.vectorEnd["coords"]["y"]
      z_vec_end = self.vectorEnd["coords"]["z"]
      x_vec_start = self.vectorStart["coords"]["x"]
      y_vec_start = self.vectorStart["coords"]["y"]
      z_vec_start = self.vectorStart["coords"]["z"]
      x_vec = x_vec_end - x_vec_start
      y_vec = y_vec_end - y_vec_start
      z_vec = z_vec_end - z_vec_start
      trans_total = math.sqrt(x_vec**2 + y_vec**2 + z_vec**2)
      self.vecLenLabelOutput.setText(str(int(trans_total)))
      totalExpTime =(float(self.osc_end_ledit.text())/float(self.osc_range_ledit.text()))*float(self.exp_time_ledit.text()) #(range/inc)*exptime
      speed = trans_total/totalExpTime
      self.vecSpeedLabelOutput.setText(str(int(speed)))
      return x_vec, y_vec, z_vec, trans_total

    def totalExpChanged(self,text):
      if (text == "oscEnd" and daq_utils.beamline == "fmx"):
        self.sampleLifetimeReadback_ledit.setStyleSheet("color : red");        
      try:
        if (float(str(self.osc_range_ledit.text())) == 0):
          if (text == "oscRange"):
            if (self.controlEnabled()):
              self.stillMode_pv.put(1)
          self.colEndLabel.setText("Number of Images: ")
          if (str(self.protoComboBox.currentText()) != "standard" and str(self.protoComboBox.currentText()) != "vector"):
            self.totalExptime_ledit.setText("----")
          else:
            try:
              totalExptime = (float(self.osc_end_ledit.text())*float(self.exp_time_ledit.text()))
            except ValueError:
              totalExptime = 0.0
            except TypeError:
              totalExptime = 0.0
            except ZeroDivisionError:
              totalExptime = 0.0
            self.totalExptime_ledit.setText('%.3f' % totalExptime)
          return
        else:
          if (text == "oscRange"):          
            if (self.controlEnabled()):
              self.standardMode_pv.put(1)
          self.colEndLabel.setText("Oscillation Range:")
      except ValueError:
        return
          
      if (str(self.protoComboBox.currentText()) != "standard" and str(self.protoComboBox.currentText()) != "vector"):
        self.totalExptime_ledit.setText("----")
      else:
        try:
          totalExptime = (float(self.osc_end_ledit.text())/(float(self.osc_range_ledit.text())))*float(self.exp_time_ledit.text())
        except ValueError:
          totalExptime = 0.0
        except TypeError:
          totalExptime = 0.0
        except ZeroDivisionError:
          totalExptime = 0.0
        self.totalExptime_ledit.setText('%.3f' % totalExptime)
        if (str(self.protoComboBox.currentText()) == "vector"):
          try:
            self.updateVectorLengthAndSpeed()
          except:
            pass
            
        try:
          if (float(self.osc_end_ledit.text()) > 4.9):
            self.fastDPCheckBox.setChecked(True)
          else:
            self.fastDPCheckBox.setChecked(False)              
        except:
          pass
        

    def resoTextChanged(self,text):
      try:
        dist_s = "%.2f" % (daq_utils.distance_from_reso(daq_utils.det_radius,float(text),daq_utils.energy2wave(float(self.energy_ledit.text())),0))
      except ValueError:
        dist_s = self.detDistRBVLabel.getEntry().text()        
      self.detDistMotorEntry.getEntry().setText(dist_s)

    def detDistTextChanged(self,text):
      try:
        reso_s = "%.2f" % (daq_utils.calc_reso(daq_utils.det_radius,float(text),daq_utils.energy2wave(float(self.energy_ledit.text())),0))
      except ValueError:
        reso_s = "50.0"
      except TypeError:
        reso_s = "50.0"
      self.setGuiValues({'resolution':reso_s})
      
    def energyTextChanged(self,text):
      dist_s = "%.2f" % (daq_utils.distance_from_reso(daq_utils.det_radius,float(self.resolution_ledit.text()),float(text),0))
      self.detDistMotorEntry.getEntry().setText(dist_s)

    #code below and its application from: https://snorfalorpagus.net/blog/2014/08/09/validating-user-input-in-pyqt4-using-qvalidator/
    def checkEntryState(self, *args, **kwargs):
      sender = self.sender()
      validator = sender.validator()
      state = validator.validate(sender.text(), 0)[0]
      if state == QtGui.QValidator.Intermediate:
          color = '#fff79a' # yellow
      elif state == QtGui.QValidator.Invalid:
          color = '#f6989d' # red
      else:
          color = '#ffffff' # white
      sender.setStyleSheet('QLineEdit { background-color: %s }' % color)

    def validateAllFields(self):
        fields_dict = {self.exp_time_ledit: {'name': 'exposure time', 'minmax': VALID_EXP_TIMES},
                        self.detDistMotorEntry.getEntry(): {'name': 'detector distance', 'minmax': VALID_DET_DIST},
                        self.totalExptime_ledit: {'name': 'total exposure time', 'minmax': VALID_TOTAL_EXP_TIMES}}

        return self.validateFields(fields_dict)

    def validateFields(self, field_values_dict):
      for field, value in field_values_dict.items():
        values = value['minmax']
        field_name = value['name']
        logger.info('validateFields: %s %s %s' % (field_name, field.text(), values))
        try:
          val = float(field.text())
          logger.info('>= min: %s <= max: %s' % (val >= values['fmx']['min'], val <= values['fmx']['max']))
        except: #total exposure time is '----' for rasters, so just ignore
          pass
        if field.text() == '----': #special case: total exp time not calculated for non-standard, non-vector experiments
            continue
        if field.validator().validate(field.text(),0)[0] != QtGui.QValidator.Acceptable:
          self.popupServerMessage('Invalid value for field %s! must be between %s and %s' % (field_name, values[daq_utils.beamline]["min"], values[daq_utils.beamline]["max"]))
          return False
      return True

    def protoRadioToggledCB(self, text):
      if (self.protoStandardRadio.isChecked()):
        self.protoComboBox.setCurrentIndex(self.protoComboBox.findText("standard"))
        self.protoComboActivatedCB(text)        
      elif (self.protoRasterRadio.isChecked()):
        self.protoComboBox.setCurrentIndex(self.protoComboBox.findText("raster"))          
        self.protoComboActivatedCB(text)
      elif (self.protoVectorRadio.isChecked()):
        self.protoComboBox.setCurrentIndex(self.protoComboBox.findText("vector"))          
        self.protoComboActivatedCB(text)
      else:
        pass

    def beamsizeComboActivatedCB(self, text):
      comm_s = "set_beamsize(\"" + str(text[0:2]) + "\",\"" + str(text[2:4]) + "\")"
      logger.info(comm_s)
      self.send_to_server(comm_s)      

    def protoComboActivatedCB(self, text):
      self.showProtParams()
      protocol = str(self.protoComboBox.currentText())
      if (protocol == "raster" or protocol == "stepRaster" or protocol == "rasterScreen" or protocol == "specRaster"):
        self.vidActionRasterDefRadio.setChecked(True)
      else:
        self.vidActionC2CRadio.setChecked(True)
      if (protocol == "raster"):
        self.protoRasterRadio.setChecked(True)
        self.osc_start_ledit.setEnabled(False)
        self.osc_end_ledit.setEnabled(False)
        self.setGuiValues({'osc_range':getBlConfig("rasterDefaultWidth"), 'exp_time':getBlConfig("rasterDefaultTime"), 'transmission':getBlConfig("rasterDefaultTrans")})
      elif (protocol == "rasterScreen"):
        self.osc_start_ledit.setEnabled(False)
        self.osc_end_ledit.setEnabled(False)
        self.setGuiValues({'osc_range':getBlConfig("rasterDefaultWidth"), 'exp_time':getBlConfig("rasterDefaultTime"), 'transmission':getBlConfig("rasterDefaultTrans")})
        self.protoOtherRadio.setChecked(True)        
      elif (protocol == "standard"):
        self.protoStandardRadio.setChecked(True)
        self.setGuiValues({'osc_range':getBlConfig("screen_default_width"), 'exp_time':getBlConfig("screen_default_time"), 'transmission':getBlConfig("stdTrans")})
        self.osc_start_ledit.setEnabled(True)
        self.osc_end_ledit.setEnabled(True)
      elif (protocol == "burn"):
        self.fastDPCheckBox.setChecked(False)        
        self.setGuiValues({'osc_range':"0.0", 'exp_time':getBlConfig("burnDefaultTime"), 'transmission':getBlConfig("burnDefaultTrans")})
        screenWidth = float(getBlConfig("burnDefaultNumFrames"))
        self.setGuiValues({'osc_end':screenWidth})
        self.osc_start_ledit.setEnabled(True)
        self.osc_end_ledit.setEnabled(True)
        
      elif (protocol == "vector"):
        self.setGuiValues({'osc_range':getBlConfig("screen_default_width"), 'exp_time':getBlConfig("screen_default_time"), 'transmission':getBlConfig("stdTrans")})
        self.osc_start_ledit.setEnabled(True)
        self.osc_end_ledit.setEnabled(True)
        self.protoVectorRadio.setChecked(True)
      else:
        self.protoOtherRadio.setChecked(True)
      self.totalExpChanged("")
            

    def rasterEvalComboActivatedCB(self, text):
      db_lib.beamlineInfo(daq_utils.beamline,'rasterScoreFlag',info_dict={"index":self.rasterEvalComboBox.findText(str(text))})
      if (self.currentRasterCellList != []):
        self.reFillPolyRaster()


    def  popBaseDirectoryDialogCB(self):
      fname = QtWidgets.QFileDialog.getExistingDirectory(self, 'Choose Directory', '',QtWidgets.QFileDialog.DontUseNativeDialog)      
      if (fname != ""):
        self.dataPathGB.setBasePath_ledit(fname)


    def popImportDialogCB(self):
      self.timerHutch.stop()
      self.timerSample.stop()            
      fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose Spreadsheet File', '',filter="*.xls *.xlsx",options=QtWidgets.QFileDialog.DontUseNativeDialog)
      self.timerSample.start(0)            
      self.timerHutch.start(HUTCH_TIMER_DELAY)            
      if (fname != ""):
        logger.info(fname)
        comm_s = "importSpreadsheet(\""+str(fname[0])+"\")"
        logger.info(comm_s)
        self.send_to_server(comm_s)
        
    def setUserModeCB(self):
      self.vidActionDefineCenterRadio.setEnabled(False)

    def setExpertModeCB(self):
      self.vidActionDefineCenterRadio.setEnabled(True)
        

    def upPriorityCB(self): #neither of these are very elegant, and might even be glitchy if overused
      currentPriority = self.selectedSampleRequest["priority"]
      if (currentPriority<1):
        return
      orderedRequests = db_lib.getOrderedRequestList(daq_utils.beamline)
      for i in range(len(orderedRequests)):
        if (orderedRequests[i]["sample"] == self.selectedSampleRequest["sample"]):
          if (i<2):
            self.topPriorityCB()
          else:
            priority = (orderedRequests[i-2]["priority"] + orderedRequests[i-1]["priority"])/2
            if (currentPriority == priority):
              priority = priority+20
            db_lib.updatePriority(self.selectedSampleRequest["uid"],priority)
      self.treeChanged_pv.put(1)
            
      
    def downPriorityCB(self):
      currentPriority = self.selectedSampleRequest["priority"]
      if (currentPriority<1):
        return
      orderedRequests = db_lib.getOrderedRequestList(daq_utils.beamline)
      for i in range(len(orderedRequests)):
        if (orderedRequests[i]["sample"] == self.selectedSampleRequest["sample"]):
          if ((len(orderedRequests)-i) < 3):
            self.bottomPriorityCB()
          else:
            priority = (orderedRequests[i+1]["priority"] + orderedRequests[i+2]["priority"])/2
            if (currentPriority == priority):
              priority = priority-20
            db_lib.updatePriority(self.selectedSampleRequest["uid"],priority)
      self.treeChanged_pv.put(1)


    def topPriorityCB(self):
      currentPriority = self.selectedSampleRequest["priority"]
      if (currentPriority<1):
        return
      priority = int(self.getMaxPriority())
      priority = priority+100
      db_lib.updatePriority(self.selectedSampleRequest["uid"],priority)
      self.treeChanged_pv.put(1)


    def bottomPriorityCB(self):
      currentPriority = self.selectedSampleRequest["priority"]
      if (currentPriority<1):
        return
      priority = int(self.getMinPriority())
      priority = priority-100
      db_lib.updatePriority(self.selectedSampleRequest["uid"],priority)
      self.treeChanged_pv.put(1)
      

    def dewarViewToggledCB(self,identifier):
      self.selectedSampleRequest = {}
#should probably clear textfields here too
      if (identifier == "dewarView"):
        if (self.dewarViewRadio.isChecked()):
          self.dewarTree.refreshTreeDewarView()
      else:
        if (self.priorityViewRadio.isChecked()):
          self.dewarTree.refreshTreePriorityView()

    def dewarViewToggleCheckCB(self):
      if (self.dewarViewRadio.isChecked()):
        self.dewarTree.refreshTreeDewarView()
      else:
        self.dewarTree.refreshTreePriorityView()

    def moveOmegaCB(self):
      comm_s = "mvaDescriptor(\"omega\"," + str(self.sampleOmegaMoveLedit.getEntry().text()) + ")"
      logger.info(comm_s)
      self.send_to_server(comm_s)
      

    def moveEnergyCB(self):
      energyRequest = float(str(self.energy_ledit.text()))
      if (abs(energyRequest-self.energy_pv.get()) > 10.0):
        self.popupServerMessage("Energy change must be less than 10 ev")
        return
      else:        
        comm_s = "mvaDescriptor(\"energy\"," + str(self.energy_ledit.text()) + ")"
        logger.info(comm_s)        
        self.send_to_server(comm_s)

    def calcLifetimeCB(self):
      if (not os.path.exists("2vb1.pdb")):
        os.system("ln -s $CONFIGDIR/2vb1.pdb .")
        os.system("mkdir rd3d")
        os.system("chmod 777 rd3d")        
      
      energyReadback = self.energy_pv.get()/1000.0
      sampleFlux = self.sampleFluxPV.get()
      logger.info("sample flux = " + str(sampleFlux))      
      try:
        vecLen_s = self.vecLenLabelOutput.text()
        if (vecLen_s != "---"):
          vecLen = float(vecLen_s)
        else:
          vecLen = 0
      except:
        vecLen = 0
      wedge = float(self.osc_end_ledit.text())
      try:
        lifeTime = raddoseLib.fmx_expTime_to_10MGy(beamsizeV = 3.0, beamsizeH = 5.0, vectorL = vecLen, energy = energyReadback, wedge = wedge, flux = sampleFlux, verbose = True)          
        lifeTime_s = "%.2f" % (lifeTime)
      except:
        lifeTime_s = "0.00"
      self.sampleLifetimeReadback_ledit.setText(lifeTime_s)
      self.sampleLifetimeReadback_ledit.setStyleSheet("color : green");
      

    def setTransCB(self):
      if (float(self.transmission_ledit.text()) > 1.0 or float(self.transmission_ledit.text()) < 0.001):
        self.popupServerMessage("Transmission must be 0.001-1.0")
        return
      comm_s = "setTrans(" + str(self.transmission_ledit.text()) + ")"
      logger.info(comm_s)
      self.send_to_server(comm_s)

    def setDCStartCB(self):
      currentPos = float(self.sampleOmegaRBVLedit.getEntry().text())%360.0
      self.setGuiValues({'osc_start':currentPos})
      
      
    def moveDetDistCB(self):
      comm_s = "mvaDescriptor(\"detectorDist\"," + str(self.detDistMotorEntry.getEntry().text()) + ")"
      logger.info(comm_s)
      self.send_to_server(comm_s)

    def omegaTweakNegCB(self):
      tv = float(self.omegaTweakVal_ledit.text())
      tweakVal = 0.0-tv
      if (self.controlEnabled()):
        self.omegaTweak_pv.put(tweakVal)
      else:
        self.popupServerMessage("You don't have control")
        
    def omegaTweakPosCB(self):
      tv = float(self.omegaTweakVal_ledit.text())
      if (self.controlEnabled()):
        self.omegaTweak_pv.put(tv)
      else:
        self.popupServerMessage("You don't have control")

    def focusTweakCB(self,tv):
      tvf = float(tv)        
      if (self.controlEnabled()):
        tvY = tvf*(math.cos(math.radians(90.0 + self.motPos["omega"]))) #these are opposite C2C
        tvZ = tvf*(math.sin(math.radians(90.0 + self.motPos["omega"])))
        self.sampyTweak_pv.put(tvY)
        self.sampzTweak_pv.put(tvZ)        
      else:
        self.popupServerMessage("You don't have control")

    def omegaTweakCB(self,tv):
      tvf = float(tv)
      if (self.controlEnabled()):
        self.omegaTweak_pv.put(tvf)
        time.sleep(0.05)
      else:
        self.popupServerMessage("You don't have control")

    def autoCenterLoopCB(self):
      logger.info("auto center loop")
      self.send_to_server("loop_center_xrec()")
      
    def autoRasterLoopCB(self):
      self.selectedSampleID = self.selectedSampleRequest["sample"]
      comm_s = "autoRasterLoop(" + str(self.selectedSampleID) + ")"
      self.send_to_server(comm_s)


    def runRastersCB(self):
      comm_s = "snakeRaster(" + str(self.selectedSampleRequest["uid"]) + ")"
      self.send_to_server(comm_s)
      
    def drawInteractiveRasterCB(self): # any polygon for now, interactive or from xrec
      for i in range(len(self.polyPointItems)):
        self.scene.removeItem(self.polyPointItems[i])
      polyPointItems = []
      pen = QtGui.QPen(QtCore.Qt.red)
      brush = QtGui.QBrush(QtCore.Qt.red)
      points = []
      polyPoints = []      
      if (self.click_positions != []): #use the user clicks
        if (len(self.click_positions) == 2): #draws a single row or column
          logger.info("2-click raster")
          polyPoints.append(self.click_positions[0])
          point = QtCore.QPointF(self.click_positions[0].x(),self.click_positions[1].y())
          polyPoints.append(point)
          point = QtCore.QPointF(self.click_positions[0].x()+2,self.click_positions[1].y())
          polyPoints.append(point)          
          point = QtCore.QPointF(self.click_positions[0].x()+2,self.click_positions[0].y())
          polyPoints.append(point)
          self.rasterPoly = QtWidgets.QGraphicsPolygonItem(QtGui.QPolygonF(polyPoints))
        else:
          self.rasterPoly = QtWidgets.QGraphicsPolygonItem(QtGui.QPolygonF(self.click_positions))
      else:
        return
      self.polyBoundingRect = self.rasterPoly.boundingRect()
      raster_w = int(self.polyBoundingRect.width())
      raster_h = int(self.polyBoundingRect.height())
      center_x = int(self.polyBoundingRect.center().x())
      center_y = int(self.polyBoundingRect.center().y())
      stepsizeXPix = self.screenXmicrons2pixels(float(self.rasterStepEdit.text()))
      stepsizeYPix = self.screenYmicrons2pixels(float(self.rasterStepEdit.text()))      
      self.click_positions = []
      self.definePolyRaster(raster_w,raster_h,stepsizeXPix,stepsizeYPix,center_x,center_y)


    def measurePolyCB(self):
      for i in range(len(self.polyPointItems)):
        self.scene.removeItem(self.polyPointItems[i])
      if (self.measureLine != None):
        self.scene.removeItem(self.measureLine)
      self.polyPointItems = []
        
      pen = QtGui.QPen(QtCore.Qt.red)
      brush = QtGui.QBrush(QtCore.Qt.red)
      points = []
      if (self.click_positions != []): #use the user clicks
        if (len(self.click_positions) == 2): #draws a single row or column
          self.measureLine = self.scene.addLine(self.click_positions[0].x(),self.click_positions[0].y(),self.click_positions[1].x(),self.click_positions[1].y(), pen)
      length = self.measureLine.line().length()
      fov = self.getCurrentFOV()
      lineMicronsX = int(round(length * (fov["x"]/daq_utils.screenPixX)))
      logger.info("linelength = " + str(lineMicronsX))      
      self.click_positions = []

      
    def center3LoopCB(self):
      logger.info("3-click center loop")
      self.threeClickCount = 1
      self.click3Button.setStyleSheet("background-color: yellow")
      self.send_to_server("mvaDescriptor(\"omega\",0)")
      

    def fillPolyRaster(self,rasterReq,waitTime=1): #at this point I should have a drawn polyRaster
      time.sleep(waitTime)
      logger.info("filling poly for " + str(rasterReq["uid"]))
      resultCount = len(db_lib.getResultsforRequest(rasterReq["uid"]))
      rasterResults = db_lib.getResultsforRequest(rasterReq["uid"])
      rasterResult = {}
      for i in range (0,len(rasterResults)):
        if (rasterResults[i]['result_type'] == 'rasterResult'):
          rasterResult = rasterResults[i]
          break
      try:
        rasterDef = rasterReq["request_obj"]["rasterDef"]
      except KeyError:
        db_lib.deleteRequest(rasterReq["uid"])
        return
      rasterListIndex = 0
      for i in range(len(self.rasterList)):
        if (self.rasterList[i] != None):
          if (self.rasterList[i]["uid"] == rasterReq["uid"]):
            rasterListIndex = i
      if (rasterResult == {}):
        return

      try:
        currentRasterGroup = self.rasterList[rasterListIndex]["graphicsItem"]
      except IndexError as e:
        logger.error('IndexError while getting raster group: %s' % e) 
        return
      self.currentRasterCellList = currentRasterGroup.childItems()
      cellResults = rasterResult["result_obj"]["rasterCellResults"]['resultObj']
      numLines = len(cellResults)
      cellResults_array = [{} for i in range(numLines)]
      my_array = np.zeros(numLines)
      spotLineCounter = 0
      cellIndex=0
      rowStartIndex = 0
      rasterEvalOption = str(self.rasterEvalComboBox.currentText())
      lenX = abs(rasterDef["rowDefs"][0]["end"]["x"] - rasterDef["rowDefs"][0]["start"]["x"]) #ugly for tile flip/noflip
      for i in range(len(rasterDef["rowDefs"])): #this is building up "my_array" with the rasterEvalOption result, and numpy can then be run against the array. 2/16, I think cellResultsArray not needed
        rowStartIndex = spotLineCounter
        numsteps = rasterDef["rowDefs"][i]["numsteps"]
        for j in range(numsteps):
          try:
            cellResult = cellResults[spotLineCounter]
          except IndexError:
            logger.error("caught index error #1")
            logger.error("numlines = " + str(numLines))
            logger.error("expected: " + str(len(rasterDef["rowDefs"])*numsteps))
            return #means a raster failure, and not enough data to cover raster, caused a gui crash
          try:
            spotcount = cellResult["spot_count_no_ice"]
            filename =  cellResult["image"]            
          except TypeError:
            spotcount = 0
            filename = "empty"

          if (lenX > 180 and self.scannerType == "PI"): #this is trying to figure out row direction
            cellIndex = spotLineCounter
          else:
            if (i%2 == 0): #this is trying to figure out row direction            
              cellIndex = spotLineCounter
            else:
              cellIndex = rowStartIndex + ((numsteps-1)-j)
          try:
            if (rasterEvalOption == "Spot Count"):
              my_array[cellIndex] = spotcount 
            elif (rasterEvalOption == "Intensity"):
              my_array[cellIndex] = cellResult["total_intensity"]
            else:
              if (float(cellResult["d_min"]) == -1):
                my_array[cellIndex] = 50.0
              else:
                my_array[cellIndex] = float(cellResult["d_min"])
          except IndexError:
            logger.error("caught index error #2")
            logger.error("numlines = " + str(numLines))
            logger.error("expected: " + str(len(rasterDef["rowDefs"])*numsteps))
            return #means a raster failure, and not enough data to cover raster, caused a gui crash
          cellResults_array[cellIndex] = cellResult #instead of just grabbing filename, get everything. Not sure why I'm building my own list of results. How is this different from cellResults?
#I don't think cellResults_array is different from cellResults, could maybe test that below by subtituting one for the other. It may be a remnant of trying to store less than the whole result set.          
          spotLineCounter+=1
      floor = np.amin(my_array)
      ceiling = np.amax(my_array)
      cellCounter = 0     
      for i in range(len(rasterDef["rowDefs"])):
        rowCellCount = 0
        for j in range(rasterDef["rowDefs"][i]["numsteps"]):
          cellResult = cellResults_array[cellCounter]
          try:
            spotcount = int(cellResult["spot_count_no_ice"])
            cellFilename = cellResult["image"]
            d_min =  float(cellResult["d_min"])
            if (d_min == -1):
              d_min = 50.0 #trying to handle frames with no spots
            total_intensity =  int(cellResult["total_intensity"])
          except TypeError:
            spotcount = 0
            cellFilename = "empty"
            d_min =  50.0
            total_intensity = 0
              
          if (rasterEvalOption == "Spot Count"):
            param = spotcount 
          elif (rasterEvalOption == "Intensity"):
            param = total_intensity
          else:
            param = d_min
          if (ceiling == 0):
            color_id = 255
          elif ceiling == floor:
            if rasterEvalOption == "Resolution":
              color_id = 0
            else:
              color_id = 255
          elif (rasterEvalOption == "Resolution"):
            color_id = int(255.0*(float(param-floor)/float(ceiling-floor)))
          else:
            color_id = int(255-(255.0*(float(param-floor)/float(ceiling-floor))))
          self.currentRasterCellList[cellCounter].setBrush(QtGui.QBrush(QtGui.QColor(0,255-color_id,0,127)))
          self.currentRasterCellList[cellCounter].setData(0,spotcount)
          self.currentRasterCellList[cellCounter].setData(1,cellFilename)
          self.currentRasterCellList[cellCounter].setData(2,d_min)
          self.currentRasterCellList[cellCounter].setData(3,total_intensity)
          cellCounter+=1
    
    def takeRasterSnapshot(self,rasterReq):
      request_obj = rasterReq["request_obj"]        
      directory = request_obj["directory"]
      filePrefix = request_obj['file_prefix']
      basePath = request_obj["basePath"]
      visitName = daq_utils.getVisitName()
      jpegDirectory = visitName + "/jpegs/" + directory[directory.find(visitName)+len(visitName):len(directory)]        
      fullJpegDirectory = basePath + "/" + jpegDirectory
      if (not os.path.exists(fullJpegDirectory)):
        os.system("mkdir -p " + fullJpegDirectory)
      jpegImagePrefix = fullJpegDirectory+"/"+filePrefix     
      jpegImageFilename = jpegImagePrefix+".jpg"
      jpegImageThumbFilename = jpegImagePrefix+"t.jpg"
      logger.info("saving raster snapshot")
      self.saveVidSnapshotCB("Raster Result from sample " + str(rasterReq["request_obj"]["file_prefix"]),useOlog=False,reqID=rasterReq["uid"],rasterHeatJpeg=jpegImageFilename)
      self.saveVidSnapshotCB("Raster Result from sample " + str(rasterReq["request_obj"]["file_prefix"]),useOlog=False,reqID=rasterReq["uid"],rasterHeatJpeg=jpegImageFilename)
      ispybLib.insertRasterResult(rasterReq,visitName)



    def reFillPolyRaster(self):      
      rasterEvalOption = str(self.rasterEvalComboBox.currentText())
      for i in range(len(self.rasterList)):
        if (self.rasterList[i] != None):
          currentRasterGroup = self.rasterList[i]["graphicsItem"]
          currentRasterCellList = currentRasterGroup.childItems()          
          my_array = np.zeros(len(currentRasterCellList))
          for i in range (0,len(currentRasterCellList)): #first loop is to get floor and ceiling
            cellIndex = i
            if (rasterEvalOption == "Spot Count"):
              spotcount = currentRasterCellList[i].data(0)
              if not isinstance(spotcount, int):
                spotcount = int(spotcount)
              my_array[cellIndex] = spotcount 
            elif (rasterEvalOption == "Intensity"):
              total_intensity  = currentRasterCellList[i].data(3)
              if not isinstance(total_intensity, int):
                total_intensity = int(total_intensity)
              my_array[cellIndex] = total_intensity
            else:
              d_min = currentRasterCellList[i].data(2)
              if not isinstance(d_min, float):
                d_min = float(d_min)
              if (d_min == -1):
                d_min = 50.0 #trying to handle frames with no spots
              my_array[cellIndex] = d_min
          floor = np.amin(my_array)
          ceiling = np.amax(my_array)
          for i in range (0,len(currentRasterCellList)):
            if (rasterEvalOption == "Spot Count") or (rasterEvalOption == "Intensity"):
              param = my_array[i] 
            else:
              d_min = my_array[i]
              if (d_min == -1):
                d_min = 50.0 #trying to handle frames with no spots
              param = d_min
            if (ceiling == 0):
              color_id = 255
            elif ceiling == floor:
              if rasterEvalOption == "Resolution":
                color_id = 0
              else:
                color_id = 255
            elif (rasterEvalOption == "Resolution"):
              color_id = int(255.0*(float(param-floor)/float(ceiling-floor)))
            else:
              color_id = int(255-(255.0*(float(param-floor)/float(ceiling-floor))))
            currentRasterCellList[i].setBrush(QtGui.QBrush(QtGui.QColor(0,255-color_id,0,127)))

      
        
    def saveCenterCB(self):
      pen = QtGui.QPen(QtCore.Qt.magenta)
      brush = QtGui.QBrush(QtCore.Qt.magenta)
      markWidth = 10
      marker = self.scene.addEllipse(self.centerMarker.x()-(markWidth/2.0)-1+self.centerMarkerCharOffsetX,self.centerMarker.y()-(markWidth/2.0)-1+self.centerMarkerCharOffsetY,markWidth,markWidth,pen,brush)
      marker.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)            
      self.centeringMark = {"sampCoords":{"x":self.sampx_pv.get(),"y":self.sampy_pv.get(),"z":self.sampz_pv.get()},"graphicsItem":marker,"centerCursorX":self.centerMarker.x(),"centerCursorY":self.centerMarker.y()}
      self.centeringMarksList.append(self.centeringMark)
 

    def selectAllCenterCB(self):
      logger.info("select all center")
      for i in range(len(self.centeringMarksList)):
        self.centeringMarksList[i]["graphicsItem"].setSelected(True)        


    def lightUpCB(self):
      self.send_to_server("backlightBrighter()")      

    def lightDimCB(self):
      self.send_to_server("backlightDimmer()")
      
    def eraseRastersCB(self):
      if (self.rasterList != []):
        for i in range(len(self.rasterList)):
          if (self.rasterList[i] != None):
            self.scene.removeItem(self.rasterList[i]["graphicsItem"])
        self.rasterList = []
        self.rasterDefList = []
        self.currentRasterCellList = []
      

    def eraseCB(self):
      self.click_positions = []
      if (self.measureLine != None):
        self.scene.removeItem(self.measureLine)
      for i in range(len(self.centeringMarksList)):
        self.scene.removeItem(self.centeringMarksList[i]["graphicsItem"])        
      self.centeringMarksList = []
      for i in range(len(self.polyPointItems)):
        self.scene.removeItem(self.polyPointItems[i])
      self.polyPointItems = []
      if (self.rasterList != []):
        for i in range(len(self.rasterList)):
          if (self.rasterList[i] != None):
            self.scene.removeItem(self.rasterList[i]["graphicsItem"])
        self.rasterList = []
        self.rasterDefList = []
        self.currentRasterCellList = []
      self.clearVectorCB()
      if (self.rasterPoly != None):      
        self.scene.removeItem(self.rasterPoly)
      self.rasterPoly =  None


    def eraseDisplayCB(self): #use this for things like zoom change. This is not the same as getting rid of all rasters.
      if (self.rasterList != []):
        for i in range(len(self.rasterList)):
          if (self.rasterList[i] != None):
            self.scene.removeItem(self.rasterList[i]["graphicsItem"])
        self.rasterList = []
        return   #short circuit
      if (self.rasterPoly != None):      
        self.scene.removeItem(self.rasterPoly)


    def getCurrentFOV(self):
      fov = {"x":0.0,"y":0.0}
      if (self.zoom2Radio.isChecked()):  #lowmagzoom      
        fov["x"] = daq_utils.lowMagFOVx/2.0
        fov["y"] = daq_utils.lowMagFOVy/2.0
      elif (self.zoom1Radio.isChecked()):
        fov["x"] = daq_utils.lowMagFOVx
        fov["y"] = daq_utils.lowMagFOVy
      elif (self.zoom4Radio.isChecked()):        
        fov["x"] = daq_utils.highMagFOVx/2.0
        fov["y"] = daq_utils.highMagFOVy/2.0
      else:
        fov["x"] = daq_utils.highMagFOVx
        fov["y"] = daq_utils.highMagFOVy
      return fov


    def screenXPixels2microns(self,pixels):
      fov = self.getCurrentFOV()
      fovX = fov["x"]
      return float(pixels)*(fovX/daq_utils.screenPixX)

    def screenYPixels2microns(self,pixels):
      fov = self.getCurrentFOV()
      fovY = fov["y"]
      return float(pixels)*(fovY/daq_utils.screenPixY)

    def screenXmicrons2pixels(self,microns):
      fov = self.getCurrentFOV()
      fovX = fov["x"]
      return int(round(microns*(daq_utils.screenPixX/fovX)))

    def screenYmicrons2pixels(self,microns):
      fov = self.getCurrentFOV()
      fovY = fov["y"]
      return int(round(microns*(daq_utils.screenPixY/fovY)))



    def definePolyRaster(self,raster_w,raster_h,stepsizeXPix,stepsizeYPix,point_x,point_y): #all come in as pixels, raster_w and raster_h are bounding box of drawn graphic
#raster status - 0=nothing done, 1=run, 2=displayed
      stepTime = float(self.exp_time_ledit.text())
      stepsize =float(self.rasterStepEdit.text())
      if ((stepsize/1000.0)/stepTime > 2.0):
        self.popupServerMessage("Stage speed exceeded. Increase exposure time, or decrease step size. Limit is 2mm/s.")
        self.eraseCB()        
        return
          
      try:
        beamWidth = float(self.beamWidth_ledit.text())
        beamHeight = float(self.beamHeight_ledit.text())
      except ValueError:
        logger.error('bad value for beam width or beam height')
        self.popupServerMessage('bad value for beam width or beam height')
        return
      if (self.scannerType == "PI"):
        rasterDef = {"rasterType":"normal","beamWidth":beamWidth,"beamHeight":beamHeight,"status":RasterStatus.NEW.value,"x":self.sampx_pv.get()+self.sampFineX_pv.get(),"y":self.sampy_pv.get()+self.sampFineY_pv.get(),"z":self.sampz_pv.get()+self.sampFineZ_pv.get(),"omega":self.omega_pv.get(),"stepsize":stepsize,"rowDefs":[]} #just storing step as microns, not using her
      else:
        rasterDef = {"rasterType":"normal","beamWidth":beamWidth,"beamHeight":beamHeight,"status":RasterStatus.NEW.value,"x":self.sampx_pv.get(),"y":self.sampy_pv.get(),"z":self.sampz_pv.get(),"omega":self.omega_pv.get(),"stepsize":stepsize,"rowDefs":[]} #just storing step as microns, not using here      
      numsteps_h = int(raster_w/stepsizeXPix) #raster_w = width,goes to numsteps horizonatl
      numsteps_v = int(raster_h/stepsizeYPix)
      if (numsteps_h == 2):
        numsteps_h = 1 #fix slop in user single line attempt
      if (numsteps_h%2 == 0): # make odd numbers of rows and columns
        numsteps_h = numsteps_h + 1
      if (numsteps_v%2 == 0):
        numsteps_v = numsteps_v + 1
      rasterDef["numCells"] = numsteps_h * numsteps_v
      point_offset_x = -(numsteps_h*stepsizeXPix)/2
      point_offset_y = -(numsteps_v*stepsizeYPix)/2
      if ((numsteps_h == 1) or (numsteps_v > numsteps_h and getBlConfig("vertRasterOn"))): #vertical raster
        for i in range(numsteps_h):
          rowCellCount = 0
          for j in range(numsteps_v):
            newCellX = point_x+(i*stepsizeXPix)+point_offset_x
            newCellY = point_y+(j*stepsizeYPix)+point_offset_y
            if (rowCellCount == 0): #start of a new row
              rowStartX = newCellX
              rowStartY = newCellY
            rowCellCount = rowCellCount+1
          if (rowCellCount != 0): #test for no points in this row of the bounding rect are in the poly?
            vectorStartX = self.screenXPixels2microns(rowStartX-self.centerMarker.x()-self.centerMarkerCharOffsetX)
            vectorEndX = vectorStartX 
            vectorStartY = self.screenYPixels2microns(rowStartY-self.centerMarker.y()-self.centerMarkerCharOffsetY)
            vectorEndY = vectorStartY + self.screenYPixels2microns(rowCellCount*stepsizeYPix)
            newRowDef = {"start":{"x": vectorStartX,"y":vectorStartY},"end":{"x":vectorEndX,"y":vectorEndY},"numsteps":rowCellCount}
            rasterDef["rowDefs"].append(newRowDef)
      else: #horizontal raster
        for i in range(numsteps_v):
          rowCellCount = 0
          for j in range(numsteps_h):
            newCellX = point_x+(j*stepsizeXPix)+point_offset_x
            newCellY = point_y+(i*stepsizeYPix)+point_offset_y
            if (rowCellCount == 0): #start of a new row
              rowStartX = newCellX
              rowStartY = newCellY
            rowCellCount = rowCellCount+1
          if (rowCellCount != 0): #testing for no points in this row of the bounding rect are in the poly?
            vectorStartX = self.screenXPixels2microns(rowStartX-self.centerMarker.x()-self.centerMarkerCharOffsetX)
            vectorEndX = vectorStartX + self.screenXPixels2microns(rowCellCount*stepsizeXPix) #this looks better
            vectorStartY = self.screenYPixels2microns(rowStartY-self.centerMarker.y()-self.centerMarkerCharOffsetY)
            vectorEndY = vectorStartY
            newRowDef = {"start":{"x": vectorStartX,"y":vectorStartY},"end":{"x":vectorEndX,"y":vectorEndY},"numsteps":rowCellCount}
            rasterDef["rowDefs"].append(newRowDef)
      setBlConfig("rasterDefaultWidth",float(self.osc_range_ledit.text()))
      setBlConfig("rasterDefaultTime",float(self.exp_time_ledit.text()))
      setBlConfig("rasterDefaultTrans",float(self.transmission_ledit.text()))
      
      self.addSampleRequestCB(rasterDef)
      return #short circuit


    def rasterIsDrawn(self,rasterReq):
      for i in range(len(self.rasterList)):
        if (self.rasterList[i] != None):
          if (self.rasterList[i]["uid"] == rasterReq["uid"]):
            return True
      return False
          


    def drawPolyRaster(self,rasterReq,x=-1,y=-1,z=-1): #rasterDef in microns,offset from center, need to convert to pixels to draw, mainly this is for displaying autoRasters, but also called in zoom change
      try:
        rasterDef = rasterReq["request_obj"]["rasterDef"]
      except KeyError:
        return
      beamSize = self.screenXmicrons2pixels(rasterDef["beamWidth"])
      stepsizeX = self.screenXmicrons2pixels(rasterDef["stepsize"])
      stepsizeY = self.screenYmicrons2pixels(rasterDef["stepsize"])      
      pen = QtGui.QPen(QtCore.Qt.red)
      newRasterCellList = []
      try:
        if (rasterDef["rowDefs"][0]["start"]["y"] == rasterDef["rowDefs"][0]["end"]["y"]): #this is a horizontal raster
          rasterDir = "horizontal"
        else:
          rasterDir = "vertical"
      except IndexError:
        return
      for i in range(len(rasterDef["rowDefs"])):
        rowCellCount = 0
        for j in range(rasterDef["rowDefs"][i]["numsteps"]):
          if (rasterDir == "horizontal"):
            newCellX = self.screenXmicrons2pixels(rasterDef["rowDefs"][i]["start"]["x"])+(j*stepsizeX)+self.centerMarker.x()+self.centerMarkerCharOffsetX
            newCellY = self.screenYmicrons2pixels(rasterDef["rowDefs"][i]["start"]["y"])+self.centerMarker.y()+self.centerMarkerCharOffsetY
          else:
            newCellX = self.screenXmicrons2pixels(rasterDef["rowDefs"][i]["start"]["x"])+self.centerMarker.x()+self.centerMarkerCharOffsetX
            newCellY = self.screenYmicrons2pixels(rasterDef["rowDefs"][i]["start"]["y"])+(j*stepsizeY)+self.centerMarker.y()+self.centerMarkerCharOffsetY
          if (rowCellCount == 0): #start of a new row
            rowStartX = newCellX
            rowStartY = newCellY
          newCellX = int(newCellX)
          newCellY = int(newCellY)
          newCell = RasterCell(newCellX,newCellY,stepsizeX, stepsizeY, self)
          newRasterCellList.append(newCell)
          newCell.setPen(pen)
          rowCellCount = rowCellCount+1 #really just for test of new row
      newItemGroup = RasterGroup(self)
      self.scene.addItem(newItemGroup)
      for i in range(len(newRasterCellList)):
        newItemGroup.addToGroup(newRasterCellList[i])
      newRasterGraphicsDesc = {"uid":rasterReq["uid"],"coords":{"x":rasterDef["x"],"y":rasterDef["y"],"z":rasterDef["z"],"omega":rasterDef["omega"]},"graphicsItem":newItemGroup}
      self.rasterList.append(newRasterGraphicsDesc)


    def timerHutchRefresh(self):
      try:
        # instead of the previous StringIO, use BytesIO:
        # https://stackoverflow.com/questions/41340296/how-can-pillow-open-uploaded-image-file-from-stringio-directly
        file = BytesIO(urllib.request.urlopen(getBlConfig("hutchCornerCamURL")).read())
        img = Image.open(file)
        qimage = ImageQt.ImageQt(img)
        pixmap_orig = QtGui.QPixmap.fromImage(qimage)
        self.pixmap_item_HutchCorner.setPixmap(pixmap_orig)        
      except Exception as e:
        logger.error('Exception during hutch corner cam handling: %s URL: %s' % (e, getBlConfig('hutchCornerCamURL')))
      try:
        file = BytesIO(urllib.request.urlopen(getBlConfig("hutchTopCamURL")).read())
        img = Image.open(file)
        qimage = ImageQt.ImageQt(img)
        pixmap_orig = QtGui.QPixmap.fromImage(qimage)
        self.pixmap_item_HutchTop.setPixmap(pixmap_orig)
      except Exception as e:
        logger.error('Exception during hutch top cam handling: %s URL: %s' % (e, getBlConfig('hutchTopCamURL')))
      

    def timerSampleRefresh(self):
      if self.capture is None:
        return 
      retval,self.readframe = self.capture.read()
      if self.readframe is None:
        logger.warning('no frame read from stream URL - ensure the URL does not end with newline and that the filename is correct')
        return #maybe stop the timer also???
      self.currentFrame = cv2.cvtColor(self.readframe,cv2.COLOR_BGR2RGB)
      height,width=self.currentFrame.shape[:2]
      qimage=QtGui.QImage(self.currentFrame,width,height,3*width,QtGui.QImage.Format_RGB888)
      pixmap_orig = QtGui.QPixmap.fromImage(qimage)
      self.pixmap_item.setPixmap(pixmap_orig)

    def timerEvent(self, event): #12/19 not used?
      retval,self.readframe = self.capture.read()
      if self.readframe is None:
        return #maybe stop the timer also???
      self.currentFrame = cv2.cvtColor(self.readframe,cv2.COLOR_BGR2RGB)
      height,width=self.currentFrame.shape[:2]
      qimage=QtGui.QImage(self.currentFrame,width,height,3*width,QtGui.QImage.Format_RGB888)
      pixmap_orig = QtGui.QPixmap.fromImage(qimage)
      self.pixmap_item.setPixmap(pixmap_orig)


    def sceneKey(self, event):
        if (event.key() == QtCore.Qt.Key_Delete or event.key() == QtCore.Qt.Key_Backspace):
          for i in range(len(self.rasterList)):
            if (self.rasterList[i] != None):
              if (self.rasterList[i]["graphicsItem"].isSelected()):
                try:
                  sceneReq = db_lib.getRequestByID(self.rasterList[i]["uid"])
                  if (sceneReq != None):
                    self.selectedSampleID = sceneReq["sample"]
                    db_lib.deleteRequest(sceneReq)["uid"]
                except AttributeError:
                  pass
                self.scene.removeItem(self.rasterList[i]["graphicsItem"])
                self.rasterList[i] = None
                self.treeChanged_pv.put(1)
          for i in range(len(self.centeringMarksList)):
            if (self.centeringMarksList[i] != None):
              if (self.centeringMarksList[i]["graphicsItem"].isSelected()):
                self.scene.removeItem(self.centeringMarksList[i]["graphicsItem"])        
                self.centeringMarksList[i] = None
          

    def pixelSelect(self, event):
        super(QtWidgets.QGraphicsPixmapItem, self.pixmap_item).mousePressEvent(event)
        x_click = float(event.pos().x())
        y_click = float(event.pos().y())
        penGreen = QtGui.QPen(QtCore.Qt.green)
        penRed = QtGui.QPen(QtCore.Qt.red)
        if (self.vidActionDefineCenterRadio.isChecked()):
          self.vidActionC2CRadio.setChecked(True) #because it's easy to forget defineCenter is on
          if (self.zoom4Radio.isChecked()): 
            comm_s = "changeImageCenterHighMag(" + str(x_click) + "," + str(y_click) + ",1)"
          elif (self.zoom3Radio.isChecked()):
            comm_s = "changeImageCenterHighMag(" + str(x_click) + "," + str(y_click) + ",0)"              
          if (self.zoom2Radio.isChecked()):        
            comm_s = "changeImageCenterLowMag(" + str(x_click) + "," + str(y_click) + ",1)"
          elif (self.zoom1Radio.isChecked()):
            comm_s = "changeImageCenterLowMag(" + str(x_click) + "," + str(y_click) + ",0)"              
          self.send_to_server(comm_s)
          return
        if (self.vidActionRasterDefRadio.isChecked()):
          self.click_positions.append(event.pos())
          self.polyPointItems.append(self.scene.addEllipse(x_click, y_click, 4, 4, penRed))
          if (len(self.click_positions) == 4):
            self.drawInteractiveRasterCB()
          return
        fov = self.getCurrentFOV()
        correctedC2C_x = daq_utils.screenPixCenterX + (x_click - (self.centerMarker.x()+self.centerMarkerCharOffsetX))
        correctedC2C_y = daq_utils.screenPixCenterY + (y_click - (self.centerMarker.y()+self.centerMarkerCharOffsetY))        
        if (self.threeClickCount > 0): #3-click centering
          self.threeClickCount = self.threeClickCount + 1
          comm_s = 'center_on_click(' + str(correctedC2C_x) + "," + str(correctedC2C_y) + "," + str(fov["x"]) + "," + str(fov["y"]) + "," + '"screen",jog=90)'          
        else:
          comm_s = 'center_on_click(' + str(correctedC2C_x) + "," + str(correctedC2C_y) + "," + str(fov["x"]) + "," + str(fov["y"])  + "," + '"screen",0)'
        if (not self.vidActionRasterExploreRadio.isChecked()):
          self.aux_send_to_server(comm_s)
        if (self.threeClickCount == 4):
          self.threeClickCount = 0
          self.click3Button.setStyleSheet("background-color: None")          
        return 


    def editScreenParamsCB(self):
      self.screenDefaultsDialog = ScreenDefaultsDialog(self)
      self.screenDefaultsDialog.show()


    def editSelectedRequestsCB(self):
      selmod = self.dewarTree.selectionModel()
      selection = selmod.selection()
      indexes = selection.indexes()
      singleRequest = 1
      for i in range(len(indexes)):
        item = self.dewarTree.model.itemFromIndex(indexes[i])
        itemData = str(item.data(32))
        itemDataType = str(item.data(33))
        if (itemDataType == "request"): 
          self.selectedSampleRequest = db_lib.getRequestByID(itemData)
          self.editSampleRequestCB(singleRequest)
          singleRequest = 0
      self.treeChanged_pv.put(1)



    def editSampleRequestCB(self,singleRequest):
      colRequest=self.selectedSampleRequest
      reqObj = colRequest["request_obj"]
      if not self.validateAllFields():
        return
      reqObj["sweep_start"] = float(self.osc_start_ledit.text())
      reqObj["sweep_end"] = float(self.osc_end_ledit.text())+float(self.osc_start_ledit.text())
      reqObj["img_width"] = float(self.osc_range_ledit.text())
      reqObj["exposure_time"] = float(self.exp_time_ledit.text())
      reqObj["detDist"] = float(self.detDistMotorEntry.getEntry().text())      
      reqObj["resolution"] = float(self.resolution_ledit.text())
      if (singleRequest == 1): # a touch kludgy, but I want to be able to edit parameters for multiple requests w/o screwing the data loc info
        reqObj["file_prefix"] = str(self.dataPathGB.prefix_ledit.text())
        reqObj["basePath"] = str(self.dataPathGB.base_path_ledit.text())
        reqObj["directory"] = str(self.dataPathGB.dataPath_ledit.text())
        reqObj["file_number_start"] = int(self.dataPathGB.file_numstart_ledit.text())
      reqObj["attenuation"] = float(self.transmission_ledit.text())
      reqObj["slit_width"] = float(self.beamWidth_ledit.text())
      reqObj["slit_height"] = float(self.beamHeight_ledit.text())
      reqObj["energy"] = float(self.energy_ledit.text())
      wave = daq_utils.energy2wave(float(self.energy_ledit.text()))
      reqObj["wavelength"] = wave
      reqObj["fastDP"] =(self.fastDPCheckBox.isChecked() or self.fastEPCheckBox.isChecked() or self.dimpleCheckBox.isChecked())
      reqObj["fastEP"] =self.fastEPCheckBox.isChecked()
      reqObj["dimple"] =self.dimpleCheckBox.isChecked()      
      reqObj["xia2"] =self.xia2CheckBox.isChecked()
      reqObj["protocol"] = str(self.protoComboBox.currentText())
      if (reqObj["protocol"] == "vector" or reqObj["protocol"] == "stepVector"):
        reqObj["vectorParams"]["fpp"] = int(self.vectorFPP_ledit.text())
      colRequest["request_obj"] = reqObj
      db_lib.updateRequest(colRequest)
      self.treeChanged_pv.put(1)

    def addRequestsToAllSelectedCB(self):
      if (self.protoComboBox.currentText() == "raster" or self.protoComboBox.currentText() == "stepRaster" or self.protoComboBox.currentText() == "specRaster"): #it confused people when they didn't need to add rasters explicitly
        return
      selmod = self.dewarTree.selectionModel()
      selection = selmod.selection()
      indexes = selection.indexes()
      try:
        progressInc = 100.0/float(len(indexes))
      except ZeroDivisionError:
        self.popupServerMessage("Select a sample to perform the request on!")
        return
      self.progressDialog.setWindowTitle("Creating Requests")
      self.progressDialog.show()
      for i in range(len(indexes)):
        self.progressDialog.setValue(int((i+1)*progressInc))
        item = self.dewarTree.model.itemFromIndex(indexes[i])
        itemData = str(item.data(32))
        itemDataType = str(item.data(33))        
        if (itemDataType == "sample"): 
          self.selectedSampleID = itemData
          if (getBlConfig("queueCollect") == 0):
            if (self.mountedPin_pv.get() != self.selectedSampleID):                    
              self.popupServerMessage("You can only add requests to a mounted sample, for now.")
              self.progressDialog.close()              
              return

        try:
          self.selectedSampleRequest = daq_utils.createDefaultRequest(self.selectedSampleID) #7/21/15  - not sure what this does, b/c I don't pass it, ahhh probably the commented line for prefix
        except KeyError:
          self.popupServerMessage("Please select a sample!")
          self.progressDialog.close()
          return
        if (len(indexes)>1):
          self.dataPathGB.setFilePrefix_ledit(str(self.selectedSampleRequest["request_obj"]["file_prefix"]))
          self.dataPathGB.setDataPath_ledit(str(self.selectedSampleRequest["request_obj"]["directory"]))
          self.EScanDataPathGB.setFilePrefix_ledit(str(self.selectedSampleRequest["request_obj"]["file_prefix"]))
          self.EScanDataPathGB.setDataPath_ledit(str(self.selectedSampleRequest["request_obj"]["directory"]))
        if (itemDataType != "container"):
          self.addSampleRequestCB(selectedSampleID=self.selectedSampleID)
      self.progressDialog.close()
      self.treeChanged_pv.put(1)


    def addSampleRequestCB(self,rasterDef=None,selectedSampleID=None):
      if (self.selectedSampleID != None):
        try:
          sample = db_lib.getSampleByID(self.selectedSampleID)
          propNum = sample["proposalID"]
        except KeyError:
          propNum = 999999
        if (propNum == None):
          propNum = 999999        
        if (propNum != daq_utils.getProposalID()):
          logger.info("setting proposal in add request")
          daq_utils.setProposalID(propNum,createVisit=True)

      if (getBlConfig("queueCollect") == 0):
        if (self.mountedPin_pv.get() != self.selectedSampleID):                    
          self.popupServerMessage("You can only add requests to a mounted sample, for now.")
          return
      
      if not self.validateAllFields():
        return
#skinner, not pretty below the way stuff is duplicated.
      if ((float(self.osc_end_ledit.text()) < float(self.osc_range_ledit.text())) and str(self.protoComboBox.currentText()) != "eScan"):
        self.popupServerMessage("Osc range less than Osc width")
        return

      if (self.periodicTable.isVisible()):
        if (self.periodicTable.eltCurrent != None):
          symbol = self.periodicTable.eltCurrent.symbol
          targetEdge = element_info[symbol][2]
          if (daq_utils.beamline == "fmx"):                              
            mcaRoiLo = element_info[symbol][4]
            mcaRoiHi = element_info[symbol][5]
          else:
            mcaRoiLo = self.XRFInfoDict[symbol]-25
            mcaRoiHi = self.XRFInfoDict[symbol]+25
          targetEnergy = Elements.Element[symbol]["binding"][targetEdge]
          colRequest = daq_utils.createDefaultRequest(self.selectedSampleID)
          sampleName = str(db_lib.getSampleNamebyID(colRequest["sample"]))
          runNum = db_lib.incrementSampleRequestCount(colRequest["sample"])
          (puckPosition,samplePositionInContainer,containerID) = db_lib.getCoordsfromSampleID(daq_utils.beamline,colRequest["sample"])
          reqObj = get_request_object_escan(colRequest["request_obj"], self.periodicTable.eltCurrent.symbol, runNum, self.EScanDataPathGB.prefix_ledit.text(),
                                           self.EScanDataPathGB.base_path_ledit.text(), sampleName, containerID, samplePositionInContainer,
                                            self.EScanDataPathGB.file_numstart_ledit.text(), self.exp_time_ledit.text(), targetEnergy, self.escan_steps_ledit.text(),
                                            self.escan_stepsize_ledit.text())
          reqObj["detDist"] = float(self.detDistMotorEntry.getEntry().text())
          reqObj["attenuation"] = float(self.transmission_ledit.text())          
          reqObj["mcaRoiLo"] = mcaRoiLo
          reqObj["mcaRoiHi"] = mcaRoiHi

          colRequest["request_obj"] = reqObj
          newSampleRequestID = db_lib.addRequesttoSample(self.selectedSampleID,reqObj["protocol"],daq_utils.owner,reqObj,priority=5000,proposalID=daq_utils.getProposalID())
#attempt here to select a newly created request.        
          self.SelectedItemData = newSampleRequestID
          
          if (selectedSampleID == None): #this is a temp kludge to see if this is called from addAll
            self.treeChanged_pv.put(1)
        else:
          logger.info("choose an element and try again")
        return          

# I don't like the code duplication, but one case is the mounted sample and selected centerings - so it's in a loop for multiple reqs, the other requires autocenter.
      if ((self.mountedPin_pv.get() == self.selectedSampleID) and (len(self.centeringMarksList) != 0)): 
        selectedCenteringFound = 0
        for i in range(len(self.centeringMarksList)):
           if (self.centeringMarksList[i]["graphicsItem"].isSelected()):
             selectedCenteringFound = 1
             colRequest = daq_utils.createDefaultRequest(self.selectedSampleID)
             sampleName = str(db_lib.getSampleNamebyID(colRequest["sample"]))
             runNum = db_lib.incrementSampleRequestCount(colRequest["sample"])
             (puckPosition,samplePositionInContainer,containerID) = db_lib.getCoordsfromSampleID(daq_utils.beamline,colRequest["sample"])                   
             reqObj = colRequest["request_obj"]
             reqObj["runNum"] = runNum
             reqObj["sweep_start"] = float(self.osc_start_ledit.text())
             reqObj["sweep_end"] = float(self.osc_end_ledit.text())+float(self.osc_start_ledit.text())
             reqObj["img_width"] = float(self.osc_range_ledit.text())
             setBlConfig("screen_default_width",float(self.osc_range_ledit.text()))
             setBlConfig("screen_default_time",float(self.exp_time_ledit.text()))
             setBlConfig("stdTrans",float(self.transmission_ledit.text()))
             setBlConfig("screen_default_dist",float(self.detDistMotorEntry.getEntry().text()))
             reqObj["exposure_time"] = float(self.exp_time_ledit.text())
             reqObj["resolution"] = float(self.resolution_ledit.text())
             reqObj["file_prefix"] = str(self.dataPathGB.prefix_ledit.text()+"_C"+str(i+1))
             reqObj["basePath"] = str(self.dataPathGB.base_path_ledit.text())
             reqObj["directory"] = str(self.dataPathGB.base_path_ledit.text())+"/"+ str(daq_utils.getVisitName()) + "/"+sampleName+"/" + str(runNum) + "/"+db_lib.getContainerNameByID(containerID)+"_"+str(samplePositionInContainer+1)+"/"             
             reqObj["file_number_start"] = int(self.dataPathGB.file_numstart_ledit.text())
             reqObj["attenuation"] = float(self.transmission_ledit.text())
             reqObj["slit_width"] = float(self.beamWidth_ledit.text())
             reqObj["slit_height"] = float(self.beamHeight_ledit.text())
             reqObj["energy"] = float(self.energy_ledit.text())             
             wave = daq_utils.energy2wave(float(self.energy_ledit.text()))
             reqObj["wavelength"] = wave
             reqObj["detDist"] = float(self.detDistMotorEntry.getEntry().text())             
             reqObj["protocol"] = str(self.protoComboBox.currentText())
             reqObj["pos_x"] = float(self.centeringMarksList[i]["sampCoords"]["x"])
             reqObj["pos_y"] = float(self.centeringMarksList[i]["sampCoords"]["y"])
             reqObj["pos_z"] = float(self.centeringMarksList[i]["sampCoords"]["z"])
             reqObj["fastDP"] = (self.fastDPCheckBox.isChecked() or self.fastEPCheckBox.isChecked() or self.dimpleCheckBox.isChecked())
             reqObj["fastEP"] =self.fastEPCheckBox.isChecked()
             reqObj["dimple"] =self.dimpleCheckBox.isChecked()             
             reqObj["xia2"] =self.xia2CheckBox.isChecked()
             if (reqObj["protocol"] == "characterize" or reqObj["protocol"] == "ednaCol"):
               characterizationParams = {"aimed_completeness":float(self.characterizeCompletenessEdit.text()),"aimed_multiplicity":str(self.characterizeMultiplicityEdit.text()),"aimed_resolution":float(self.characterizeResoEdit.text()),"aimed_ISig":float(self.characterizeISIGEdit.text())}
               reqObj["characterizationParams"] = characterizationParams
             colRequest["request_obj"] = reqObj             
             newSampleRequestID = db_lib.addRequesttoSample(self.selectedSampleID,reqObj["protocol"],daq_utils.owner,reqObj,priority=5000,proposalID=daq_utils.getProposalID())
#attempt here to select a newly created request.        
             self.SelectedItemData = newSampleRequestID
        if (selectedCenteringFound == 0):
          message = QtWidgets.QErrorMessage(self)
          message.setModal(False)
          message.showMessage("You need to select a centering.")
      else: #autocenter or interactive
        colRequest=self.selectedSampleRequest
        try:
          sampleName = str(db_lib.getSampleNamebyID(colRequest["sample"]))
        except KeyError:
          logger.error('no sample selected')
          self.popupServerMessage('no sample selected')
          return
        (puckPosition,samplePositionInContainer,containerID) = db_lib.getCoordsfromSampleID(daq_utils.beamline,colRequest["sample"])              
        runNum = db_lib.incrementSampleRequestCount(colRequest["sample"])
        reqObj = colRequest["request_obj"]
        centeringOption = str(self.centeringComboBox.currentText())
        reqObj["centeringOption"] = centeringOption        
        if ((centeringOption == "Interactive" and self.mountedPin_pv.get() == self.selectedSampleID) or centeringOption == "Testing"): #user centered manually
          reqObj["pos_x"] = float(self.sampx_pv.get())
          reqObj["pos_y"] = float(self.sampy_pv.get())
          reqObj["pos_z"] = float(self.sampz_pv.get())
        reqObj["runNum"] = runNum
        reqObj["sweep_start"] = float(self.osc_start_ledit.text())
        reqObj["sweep_end"] = float(self.osc_end_ledit.text())+float(self.osc_start_ledit.text())
        reqObj["img_width"] = float(self.osc_range_ledit.text())
        reqObj["exposure_time"] = float(self.exp_time_ledit.text())
        if (rasterDef == None and reqObj["protocol"] != "burn"):        
          setBlConfig("screen_default_width",float(self.osc_range_ledit.text()))
          setBlConfig("screen_default_time",float(self.exp_time_ledit.text()))
          setBlConfig("stdTrans",float(self.transmission_ledit.text()))
          setBlConfig("screen_default_dist",float(self.detDistMotorEntry.getEntry().text()))          
        reqObj["resolution"] = float(self.resolution_ledit.text())
        reqObj["directory"] = str(self.dataPathGB.base_path_ledit.text())+ "/" + str(daq_utils.getVisitName()) + "/" +str(self.dataPathGB.prefix_ledit.text())+"/" + str(runNum) + "/"+db_lib.getContainerNameByID(containerID)+"_"+str(samplePositionInContainer+1)+"/"
        reqObj["basePath"] = str(self.dataPathGB.base_path_ledit.text())
        reqObj["file_prefix"] = str(self.dataPathGB.prefix_ledit.text())
        reqObj["file_number_start"] = int(self.dataPathGB.file_numstart_ledit.text())
        if (abs(reqObj["sweep_end"]-reqObj["sweep_start"])<5.0):
          reqObj["fastDP"] = False
          reqObj["fastEP"] = False
          reqObj["dimple"] = False          
        else:
          reqObj["fastDP"] = (self.fastDPCheckBox.isChecked() or self.fastEPCheckBox.isChecked() or self.dimpleCheckBox.isChecked())
          reqObj["fastEP"] =self.fastEPCheckBox.isChecked()
          reqObj["dimple"] =self.dimpleCheckBox.isChecked()          
        reqObj["xia2"] =self.xia2CheckBox.isChecked()
        reqObj["attenuation"] = float(self.transmission_ledit.text())
        reqObj["slit_width"] = float(self.beamWidth_ledit.text())
        reqObj["slit_height"] = float(self.beamHeight_ledit.text())
        reqObj["energy"] = float(self.energy_ledit.text())                  
        try:        
          wave = daq_utils.energy2wave(float(self.energy_ledit.text()))
        except ValueError:
          wave = 1.1

        reqObj["wavelength"] = wave
        reqObj["protocol"] = str(self.protoComboBox.currentText())
        try:
          reqObj["detDist"] = float(self.detDistMotorEntry.getEntry().text())
        except ValueError:
          new_distance = 502.0
          logger.error("set dist to %s in exception handler 1" % new_distance)
          reqObj["detDist"] = new_distance
        if (reqObj["protocol"] == "multiCol" or reqObj["protocol"] == "multiColQ"):
          reqObj["gridStep"] = float(self.rasterStepEdit.text())
          reqObj["diffCutoff"] = float(self.multiColCutoffEdit.text())
        if (reqObj["protocol"] == "rasterScreen"):
          reqObj["gridStep"] = float(self.rasterStepEdit.text())
        if (rasterDef != None):
          reqObj["rasterDef"] = rasterDef
          reqObj["gridStep"] = float(self.rasterStepEdit.text())
        if (reqObj["protocol"] == "characterize" or reqObj["protocol"] == "ednaCol"):
          characterizationParams = {"aimed_completeness":float(self.characterizeCompletenessEdit.text()),"aimed_multiplicity":str(self.characterizeMultiplicityEdit.text()),"aimed_resolution":float(self.characterizeResoEdit.text()),"aimed_ISig":float(self.characterizeISIGEdit.text())}
          reqObj["characterizationParams"] = characterizationParams
        if (reqObj["protocol"] == "vector" or reqObj["protocol"] == "stepVector"):
          if (float(self.osc_end_ledit.text()) < 5.0):              
            self.popupServerMessage("Vector oscillation must be at least 5.0 degrees.")
            return
          selectedCenteringFound = 1            
          try:
            x_vec, y_vec, z_vec, trans_total = self.updateVectorLengthAndSpeed()
            framesPerPoint = int(self.vectorFPP_ledit.text())
            vectorParams={"vecStart":self.vectorStart["coords"],"vecEnd":self.vectorEnd["coords"],"x_vec":x_vec,"y_vec":y_vec,"z_vec":z_vec,"trans_total":trans_total,"fpp":framesPerPoint}
            reqObj["vectorParams"] = vectorParams
          except Exception as e:
            if self.vectorStart == None:
              self.popupServerMessage("Vector start must be defined.")
              return
            elif self.vectorEnd == None:
              self.popupServerMessage("Vector end must be defined.")
              return
            logger.error('Exception while getting vector parameters: %s' % e)
            pass
        colRequest["request_obj"] = reqObj
        newSampleRequestID = db_lib.addRequesttoSample(self.selectedSampleID,reqObj["protocol"],daq_utils.owner,reqObj,priority=5000,proposalID=daq_utils.getProposalID())
#attempt here to select a newly created request.        
        self.SelectedItemData = newSampleRequestID
        newSampleRequest = db_lib.getRequestByID(newSampleRequestID)
        if (rasterDef != None):
          self.rasterDefList.append(newSampleRequest)
          self.drawPolyRaster(newSampleRequest)
      if (selectedSampleID == None): #this is a temp kludge to see if this is called from addAll
        self.treeChanged_pv.put(1)


    def cloneRequestCB(self):
      self.eraseCB()
      colRequest=self.selectedSampleRequest
      reqObj = colRequest["request_obj"]
      rasterDef = reqObj["rasterDef"]
      self.addSampleRequestCB(rasterDef)      


      
    def collectQueueCB(self):
      currentRequest = db_lib.popNextRequest(daq_utils.beamline)
      if (currentRequest == {}):
        self.addRequestsToAllSelectedCB()        
      logger.info("running queue")
      self.send_to_server("runDCQueue()")

    def warmupGripperCB(self):
      self.send_to_server("warmupGripper()")      

    def dryGripperCB(self):
      self.send_to_server("dryGripper()")      

    def enableTScreenGripperCB(self):
      self.send_to_server("enableDewarTscreen()")      

    def parkGripperCB(self):
      self.send_to_server("parkGripper()")      
      
    def openPhotonShutterCB(self):
      self.photonShutterOpen_pv.put(1)

    def popUserScreenCB(self):
      if (self.controlEnabled()):                
        self.userScreenDialog.show()
      else:
        self.popupServerMessage("You don't have control")          
      
            

    def closePhotonShutterCB(self):
      self.photonShutterClose_pv.put(1)        

  

    def removePuckCB(self):
      self.timerHutch.stop()
      self.timerSample.stop()                    
      dewarPos, ok = DewarDialog.getDewarPos(parent=self,action="remove")
      self.timerSample.start(0)            
      self.timerHutch.start(HUTCH_TIMER_DELAY)            
      

    def getVectorObject(self):
      pen = QtGui.QPen(QtCore.Qt.blue)
      brush = QtGui.QBrush(QtCore.Qt.blue)
      markWidth = 10
      vecMarker = self.scene.addEllipse(self.centerMarker.x()-(markWidth/2.0)-1+self.centerMarkerCharOffsetX,self.centerMarker.y()-(markWidth/2.0)-1+self.centerMarkerCharOffsetY,markWidth,markWidth,pen,brush)
      vectorCoords = {"x":self.sampx_pv.get(),"y":self.sampy_pv.get(),"z":self.sampz_pv.get()}
      return {"coords":vectorCoords,"graphicsitem":vecMarker,"centerCursorX":self.centerMarker.x(),"centerCursorY":self.centerMarker.y()}
 
    def setVectorStartCB(self): #save sample x,y,z
      if (self.vectorStart != None):
        self.scene.removeItem(self.vectorStart["graphicsitem"])
        try:
          self.scene.removeItem(self.vecLine)
        except AttributeError: # liekly due to vecLine not being defined yet
          pass
        self.vectorStart = None
      self.vectorStart = self.getVectorObject()

      if self.vectorStart and self.vectorEnd:
        self.drawVector()

    def drawVector(self):
      pen = QtGui.QPen(QtCore.Qt.blue)
      brush = QtGui.QBrush(QtCore.Qt.blue)
      try:
        self.updateVectorLengthAndSpeed()
      except:
        pass
      self.protoVectorRadio.setChecked(True)
      self.vecLine = self.scene.addLine(self.centerMarker.x()+self.vectorStart["graphicsitem"].x()+self.centerMarkerCharOffsetX,
                                        self.centerMarker.y()+self.vectorStart["graphicsitem"].y()+self.centerMarkerCharOffsetY,
                                        self.centerMarker.x()+self.vectorEnd["graphicsitem"].x()+self.centerMarkerCharOffsetX,
                                        self.centerMarker.y()+self.vectorEnd["graphicsitem"].y()+self.centerMarkerCharOffsetY, pen)
      self.vecLine.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)

    def setVectorEndCB(self): #save sample x,y,z
      if (self.vectorEnd != None):
        self.scene.removeItem(self.vectorEnd["graphicsitem"])
        try:
          self.scene.removeItem(self.vecLine)
        except AttributeError: # likely due to self.vecLine not being defined yet
          pass
        self.vectorEnd = None
      self.vectorEnd = self.getVectorObject()

      if self.vectorStart and self.vectorEnd:
        self.drawVector()        

    def clearVectorCB(self):
      if (self.vectorStart != None):
        self.scene.removeItem(self.vectorStart["graphicsitem"])
        self.vectorStart = None
      if (self.vectorEnd != None):
        self.scene.removeItem(self.vectorEnd["graphicsitem"])
        self.vectorEnd = None
        self.vecLenLabelOutput.setText("---")
        self.vecSpeedLabelOutput.setText("---")        
      try:
        if self.vecLine != None:
          self.scene.removeItem(self.vecLine)
      except AttributeError: # likely due to self.vecLine not defined yet
        pass

    def puckToDewarCB(self):
      while (1):
        self.timerHutch.stop()
        self.timerSample.stop()      
        puckName, ok = PuckDialog.getPuckName()
        self.timerSample.start(0)            
        self.timerHutch.start(HUTCH_TIMER_DELAY)      
        if (ok):
          self.timerHutch.stop()
          self.timerSample.stop()      
          dewarPos, ok = DewarDialog.getDewarPos(parent=self,action="add")
          self.timerSample.start(0)            
          self.timerHutch.start(HUTCH_TIMER_DELAY)      
          ipos = int(dewarPos)+1
          if (ok):
            db_lib.insertIntoContainer(daq_utils.primaryDewarName,daq_utils.beamline,ipos,db_lib.getContainerIDbyName(puckName,daq_utils.owner))
            self.treeChanged_pv.put(1)
        else:
          break


    def stopRunCB(self):
      logger.info("stopping collection")
      self.aux_send_to_server("stopDCQueue(1)")

    def stopQueueCB(self):
      logger.info("stopping queue")
      if (self.pauseQueueButton.text() == "Continue"):
        self.aux_send_to_server("continue_data_collection()")        
      else:
        self.aux_send_to_server("stopDCQueue(2)")

    def mountSampleCB(self):
      if (getBlConfig("mountEnabled") == 0):
        self.popupServerMessage("Mounting disabled!! Call staff!")
        return
      logger.info("mount selected sample")
      self.eraseCB()      
      try:
        self.selectedSampleID = self.selectedSampleRequest["sample"]
      except KeyError as e:
        logger.error('unable to get sample')
        return
      self.send_to_server("mountSample(\""+str(self.selectedSampleID)+"\")")
      self.zoom1Radio.setChecked(True)      
      self.zoomLevelToggledCB("Zoom1")
      self.protoComboBox.setCurrentIndex(self.protoComboBox.findText(str("standard")))
      self.protoComboActivatedCB("standard")

    def unmountSampleCB(self):
      logger.info("unmount sample")
      self.eraseCB()      
      self.send_to_server("unmountSample()")


    def refreshCollectionParams(self,selectedSampleRequest):
      reqObj = selectedSampleRequest["request_obj"]
      self.protoComboBox.setCurrentIndex(self.protoComboBox.findText(str(reqObj["protocol"])))
      protocol = str(reqObj["protocol"])
      if (protocol == "raster"):
        self.protoRasterRadio.setChecked(True)
      elif (protocol == "standard"):
        self.protoStandardRadio.setChecked(True)
      elif (protocol == "vector"):
        self.protoVectorRadio.setChecked(True)
      else:
        self.protoOtherRadio.setChecked(True)
      
      logger.info('osc range')
      self.setGuiValues({'osc_start':reqObj["sweep_start"], 'osc_end':reqObj["sweep_end"]-reqObj["sweep_start"], 'osc_range':reqObj["img_width"], 'exp_time':reqObj["exposure_time"], 'resolution':reqObj["resolution"], 'transmission':reqObj["attenuation"]})
      self.dataPathGB.setFileNumstart_ledit(str(reqObj["file_number_start"]))
      self.beamWidth_ledit.setText(str(reqObj["slit_width"]))
      self.beamHeight_ledit.setText(str(reqObj["slit_height"]))
      if ("fastDP" in reqObj):
        self.fastDPCheckBox.setChecked((reqObj["fastDP"] or reqObj["fastEP"] or reqObj["dimple"]))
      if ("fastEP" in reqObj):
        self.fastEPCheckBox.setChecked(reqObj["fastEP"])
      if ("dimple" in reqObj):
        self.dimpleCheckBox.setChecked(reqObj["dimple"])        
      if ("xia2" in reqObj):
        self.xia2CheckBox.setChecked(reqObj["xia2"])
      reqObj["energy"] = float(self.energy_ledit.text())
      self.energy_ledit.setText(str(reqObj["energy"]))                        
      energy_s = str(daq_utils.wave2energy(reqObj["wavelength"]))
      dist_s = str(reqObj["detDist"])
      self.detDistMotorEntry.getEntry().setText(str(dist_s))
      self.dataPathGB.setFilePrefix_ledit(str(reqObj["file_prefix"]))
      self.dataPathGB.setBasePath_ledit(str(reqObj["basePath"]))
      self.dataPathGB.setDataPath_ledit(str(reqObj["directory"]))
      if (str(reqObj["protocol"]) == "characterize" or str(reqObj["protocol"]) == "ednaCol"): 
        prefix_long = str(reqObj["directory"])+"/ref-"+str(reqObj["file_prefix"])
      else:
        prefix_long = str(reqObj["directory"])+"/"+str(reqObj["file_prefix"])
      fnumstart=reqObj["file_number_start"]

      if (str(reqObj["protocol"]) == "characterize" or str(reqObj["protocol"]) == "ednaCol" or str(reqObj["protocol"]) == "standard" or str(reqObj["protocol"]) == "vector"):
        if ("priority" in selectedSampleRequest):
          if (selectedSampleRequest["priority"] < 0 and self.albulaDispCheckBox.isChecked()):
            firstFilename = daq_utils.create_filename(prefix_long,fnumstart)            
            albulaUtils.albulaDispFile(firstFilename)            
      self.rasterStepEdit.setText(str(reqObj["gridStep"]))
      if (reqObj["gridStep"] == self.rasterStepDefs["Coarse"]):
        self.rasterGrainCoarseRadio.setChecked(True)
      elif (reqObj["gridStep"] == self.rasterStepDefs["Fine"]):
        self.rasterGrainFineRadio.setChecked(True)
      elif (reqObj["gridStep"] == self.rasterStepDefs["VFine"]):
        self.rasterGrainVFineRadio.setChecked(True)
      else:
        self.rasterGrainCustomRadio.setChecked(True)          
      rasterStep = int(reqObj["gridStep"])
      if (not self.hideRastersCheckBox.isChecked() and (str(reqObj["protocol"])== "raster" or str(reqObj["protocol"])== "stepRaster" or str(reqObj["protocol"])== "specRaster")):
        if (not self.rasterIsDrawn(selectedSampleRequest)):
          self.drawPolyRaster(selectedSampleRequest)
          self.fillPolyRaster(selectedSampleRequest)
        self.processSampMove(self.sampx_pv.get(),"x")
        self.processSampMove(self.sampy_pv.get(),"y")
        self.processSampMove(self.sampz_pv.get(),"z")
        if (abs(selectedSampleRequest["request_obj"]["rasterDef"]["omega"]-self.omega_pv.get()) > 5.0):
          comm_s = "mvaDescriptor(\"omega\"," + str(selectedSampleRequest["request_obj"]["rasterDef"]["omega"]) + ")"
          self.send_to_server(comm_s)
      if (str(reqObj["protocol"])== "eScan"):
        try:
          self.escan_steps_ledit.setText(str(reqObj["steps"]))
          self.escan_stepsize_ledit.setText(str(reqObj["stepsize"]))
          self.EScanDataPathGB.setBasePath_ledit(reqObj["basePath"])
          self.EScanDataPathGB.setDataPath_ledit(reqObj["directory"])
          self.EScanDataPathGB.setFileNumstart_ledit(str(reqObj["file_number_start"]))          
          self.EScanDataPathGB.setFilePrefix_ledit(str(reqObj["file_prefix"]))                  
          self.periodicTable.elementClicked(reqObj["element"])
        except KeyError:        
          pass
      elif (str(reqObj["protocol"])== "characterize" or str(reqObj["protocol"])== "ednaCol"):
        characterizationParams = reqObj["characterizationParams"]
        self.characterizeCompletenessEdit.setText(str(characterizationParams["aimed_completeness"]))
        self.characterizeISIGEdit.setText(str(characterizationParams["aimed_ISig"]))
        self.characterizeResoEdit.setText(str(characterizationParams["aimed_resolution"]))
        self.characterizeMultiplicityEdit.setText(str(characterizationParams["aimed_multiplicity"]))
      else: #for now, erase the rasters if a non-raster is selected, need to rationalize later
        pass
      self.showProtParams()
      


    def row_clicked(self,index): #I need "index" here? seems like I get it from selmod, but sometimes is passed
      selmod = self.dewarTree.selectionModel()
      selection = selmod.selection()
      indexes = selection.indexes()
      if (len(indexes)==0):
        return
      i = 0
      item = self.dewarTree.model.itemFromIndex(indexes[i])
      parent = indexes[i].parent()
      try:
        puck_name = parent.data()
      except AttributeError as e:
        logger.error('attribute error in row_clicked: %s', e)
        return
      itemData = str(item.data(32))
      itemDataType = str(item.data(33))
      self.SelectedItemData = itemData # an attempt to know what is selected and preserve it when refreshing the tree
      if (itemData == ""):
        logger.info("nothing there")
        return
      elif (itemDataType == "container"):
        logger.info("I'm a puck")
        return
      elif (itemDataType == "sample"):
        self.selectedSampleID = itemData
        sample = db_lib.getSampleByID(self.selectedSampleID)
        owner = sample["owner"]
        sample_name = db_lib.getSampleNamebyID(self.selectedSampleID)
        logger.info("sample in pos " + str(itemData))
        if (self.osc_start_ledit.text() == ""):
          self.selectedSampleRequest = daq_utils.createDefaultRequest(itemData,createVisit=False)
          self.refreshCollectionParams(self.selectedSampleRequest)
          if (self.stillModeStatePV.get()):
            self.setGuiValues({'osc_range':"0.0"})
          reqObj = self.selectedSampleRequest["request_obj"]
          self.dataPathGB.setFilePrefix_ledit(str(reqObj["file_prefix"]))          
          self.dataPathGB.setBasePath_ledit(reqObj["basePath"])
          self.dataPathGB.setDataPath_ledit(reqObj["directory"])
          self.EScanDataPathGB.setFilePrefix_ledit(str(reqObj["file_prefix"]))          
          self.EScanDataPathGB.setBasePath_ledit(reqObj["basePath"])
          self.EScanDataPathGB.setDataPath_ledit(reqObj["directory"])
          self.EScanDataPathGB.setFileNumstart_ledit(str(reqObj["file_number_start"]))          
          if (self.vidActionRasterDefRadio.isChecked()):
            self.protoComboBox.setCurrentIndex(self.protoComboBox.findText(str("raster")))
            self.showProtParams()
        elif (str(self.protoComboBox.currentText()) == "screen"):
          self.selectedSampleRequest = daq_utils.createDefaultRequest(itemData,createVisit=False)
          self.refreshCollectionParams(self.selectedSampleRequest)
          if (self.stillModeStatePV.get()):
            self.setGuiValue({'osc_range':"0.0"})
        else:
          self.selectedSampleRequest = daq_utils.createDefaultRequest(itemData,createVisit=False)
          reqObj = self.selectedSampleRequest["request_obj"]
          self.dataPathGB.setFilePrefix_ledit(str(reqObj["file_prefix"]))          
          self.dataPathGB.setBasePath_ledit(reqObj["basePath"])
          self.dataPathGB.setDataPath_ledit(reqObj["directory"])
          self.EScanDataPathGB.setFilePrefix_ledit(str(reqObj["file_prefix"]))          
          self.EScanDataPathGB.setBasePath_ledit(reqObj["basePath"])
          self.EScanDataPathGB.setDataPath_ledit(reqObj["directory"])
          self.EScanDataPathGB.setFileNumstart_ledit(str(reqObj["file_number_start"]))          
      else: #request
        self.selectedSampleRequest = db_lib.getRequestByID(itemData)
        reqObj = self.selectedSampleRequest["request_obj"]
        reqID = self.selectedSampleRequest["uid"]
        self.selectedSampleID = self.selectedSampleRequest["sample"]        
        sample = db_lib.getSampleByID(self.selectedSampleID)
        owner = sample["owner"]
        if (reqObj["protocol"] == "eScan"):
          try:
            if (reqObj["runChooch"]):
              resultList = db_lib.getResultsforRequest(reqID)
              if (len(resultList) > 0):
                lastResult = resultList[-1]
                if (db_lib.getResult(lastResult['uid'])["result_type"] == "choochResult"):                  
                  resultID = lastResult['uid']
                  logger.info("plotting chooch")
                  self.processChoochResult(resultID)
          except KeyError:
            logger.error('KeyError - ignoring chooch-related items, perhaps from a bad energy scan')
        self.refreshCollectionParams(self.selectedSampleRequest)


    def processXrecRasterCB(self,value=None, char_value=None, **kw):
      xrecFlag = value
      if (xrecFlag != "0"):
        self.xrecRasterSignal.emit(xrecFlag)

    def processChoochResultsCB(self,value=None, char_value=None, **kw):
      choochFlag = value
      if (choochFlag != "0"):
        self.choochResultSignal.emit(choochFlag)

    def processEnergyChangeCB(self,value=None, char_value=None, **kw):
      energyVal = value
      self.energyChangeSignal.emit(energyVal)

    def mountedPinChangedCB(self,value=None, char_value=None, **kw):
      mountedPinPos = value
      self.mountedPinSignal.emit(mountedPinPos)

    def beamSizeChangedCB(self,value=None, char_value=None, **kw):
      beamSizeFlag = value
      self.beamSizeSignal.emit(beamSizeFlag)
    
    def controlMasterChangedCB(self,value=None, char_value=None, **kw):
      controlMasterPID = value
      self.controlMasterSignal.emit(controlMasterPID)

    def zebraArmStateChangedCB(self,value=None, char_value=None, **kw):
      armState = value
      self.zebraArmStateSignal.emit(armState)
      
    def govRobotSeReachChangedCB(self,value=None, char_value=None, **kw):
      armState = value
      self.govRobotSeReachSignal.emit(armState)

    def govRobotSaReachChangedCB(self,value=None, char_value=None, **kw):
      armState = value
      self.govRobotSaReachSignal.emit(armState)

    def govRobotDaReachChangedCB(self,value=None, char_value=None, **kw):
      armState = value
      self.govRobotDaReachSignal.emit(armState)

    def govRobotBlReachChangedCB(self,value=None, char_value=None, **kw):
      armState = value
      self.govRobotBlReachSignal.emit(armState)


    def detMessageChangedCB(self,value=None, char_value=None, **kw):
      state = char_value
      self.detMessageSignal.emit(state)
      
    def sampleFluxChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.sampleFluxSignal.emit(state)
      
    def zebraPulseStateChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.zebraPulseStateSignal.emit(state)

    def stillModeStateChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.stillModeStateSignal.emit(state)

    def zebraDownloadStateChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.zebraDownloadStateSignal.emit(state)

    def zebraSentTriggerStateChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.zebraSentTriggerStateSignal.emit(state)
      
    def zebraReturnedTriggerStateChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.zebraReturnedTriggerStateSignal.emit(state)
      
    def shutterChangedCB(self,value=None, char_value=None, **kw):
      shutterVal = value        
      self.fastShutterSignal.emit(shutterVal)
      
    def gripTempChangedCB(self,value=None, char_value=None, **kw):
      gripVal = value        
      self.gripTempSignal.emit(gripVal)

    def cryostreamTempChangedCB(self, value=None, char_value=None, **kw):
      cryostreamTemp = value
      self.cryostreamTempSignal.emit(cryostreamTemp)

    def ringCurrentChangedCB(self,value=None, char_value=None, **kw):
      ringCurrentVal = value        
      self.ringCurrentSignal.emit(ringCurrentVal)

    def beamAvailableChangedCB(self,value=None, char_value=None, **kw):
      beamAvailableVal = value        
      self.beamAvailableSignal.emit(beamAvailableVal)

    def sampleExposedChangedCB(self,value=None, char_value=None, **kw):
      sampleExposedVal = value        
      self.sampleExposedSignal.emit(sampleExposedVal)
      
    def processSampMoveCB(self,value=None, char_value=None, **kw):
      posRBV = value
      motID = kw["motID"]
      self.sampMoveSignal.emit(posRBV,motID)

    def processROIChangeCB(self,value=None, char_value=None, **kw):
      posRBV = value
      ID = kw["ID"]
      self.roiChangeSignal.emit(posRBV,ID)
      

    def processHighMagCursorChangeCB(self,value=None, char_value=None, **kw):
      posRBV = value
      ID = kw["ID"]
      self.highMagCursorChangeSignal.emit(posRBV,ID)
      
    def processLowMagCursorChangeCB(self,value=None, char_value=None, **kw):
      posRBV = value
      ID = kw["ID"]
      self.lowMagCursorChangeSignal.emit(posRBV,ID)
      

    def treeChangedCB(self,value=None, char_value=None, **kw):
      if (self.processID != self.treeChanged_pv.get()):
        self.refreshTreeSignal.emit()

    def serverMessageCB(self,value=None, char_value=None, **kw):
      serverMessageVar = char_value
      self.serverMessageSignal.emit(serverMessageVar)

    def serverPopupMessageCB(self,value=None, char_value=None, **kw):
      serverMessageVar = char_value
      self.serverPopupMessageSignal.emit(serverMessageVar)

      
    def programStateCB(self, value=None, char_value=None, **kw):
      programStateVar = value
      self.programStateSignal.emit(programStateVar)

    def pauseButtonStateCB(self, value=None, char_value=None, **kw):
      pauseButtonStateVar = value
      self.pauseButtonStateSignal.emit(pauseButtonStateVar)

        
    def initUI(self):               
        self.tabs= QtWidgets.QTabWidget()
        self.comm_pv = PV(daq_utils.beamlineComm + "command_s")
        self.immediate_comm_pv = PV(daq_utils.beamlineComm + "immediate_command_s")
        self.stillModeStatePV = PV(daq_utils.pvLookupDict["stillModeStatus"])        
        self.progressDialog = QtWidgets.QProgressDialog()
        self.progressDialog.setCancelButtonText(QString())
        self.progressDialog.setModal(False)
        tab1= QtWidgets.QWidget()
        vBoxlayout1= QtWidgets.QVBoxLayout()
        splitter1 = QtWidgets.QSplitter(QtCore.Qt.Vertical,self)
        splitter1.addWidget(self.tabs)
        self.setCentralWidget(splitter1)
        splitterSizes = [600,100]
        importAction = QtWidgets.QAction('Import Spreadsheet...', self)
        importAction.triggered.connect(self.popImportDialogCB)
        modeGroup = QActionGroup(self);
        modeGroup.setExclusive(True)        
        self.userAction = QtWidgets.QAction('User Mode', self,checkable=True)
        self.userAction.triggered.connect(self.setUserModeCB)
        self.userAction.setChecked(True)
        self.expertAction = QtWidgets.QAction('Expert Mode', self,checkable=True)
        self.expertAction.triggered.connect(self.setExpertModeCB)
        self.staffAction = QtWidgets.QAction('Staff Panel...', self)
        self.staffAction.triggered.connect(self.popStaffDialogCB)
        modeGroup.addAction(self.userAction)
        modeGroup.addAction(self.expertAction)
        exitAction = QtWidgets.QAction(QtGui.QIcon('exit24.png'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.closeAll)
        self.statusBar()
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(importAction)
        fileMenu.addAction(self.userAction)
        fileMenu.addAction(self.expertAction)
        fileMenu.addAction(self.staffAction)                
        fileMenu.addAction(exitAction)
        self.setGeometry(300, 300, 1550, 1000) #width and height here. 
        self.setWindowTitle('LSDC on %s' % daq_utils.beamline)
        self.show()

    def popStaffDialogCB(self):
      if (self.controlEnabled()):
        self.staffScreenDialog = StaffScreenDialog(self)
      else:
        self.popupServerMessage("You don't have control")          
      

    def closeAll(self):
      QtWidgets.QApplication.closeAllWindows()


    def initCallbacks(self):

      self.beamSizeSignal.connect(self.processBeamSize)
      self.beamSize_pv.add_callback(self.beamSizeChangedCB)  

      self.treeChanged_pv = PV(daq_utils.beamlineComm + "live_q_change_flag")
      self.refreshTreeSignal.connect(self.dewarTree.refreshTree)
      self.treeChanged_pv.add_callback(self.treeChangedCB)  
      self.mountedPin_pv = PV(daq_utils.beamlineComm + "mounted_pin")
      self.mountedPinSignal.connect(self.processMountedPin)
      self.mountedPin_pv.add_callback(self.mountedPinChangedCB)
      det_stop_pv = daq_utils.pvLookupDict["stopEiger"]
      logger.info('setting stop Eiger detector PV: %s' % det_stop_pv)
      self.stopDet_pv = PV(det_stop_pv)
      det_reboot_pv = daq_utils.pvLookupDict["eigerIOC_reboot"]
      logger.info('setting detector ioc reboot PV: %s' % det_reboot_pv)
      self.rebootDetIOC_pv = PV(daq_utils.beamlineComm + "eigerIOC_reboot")      
      rz_pv = daq_utils.pvLookupDict["zebraReset"]
      logger.info('setting zebra reset PV: %s' % rz_pv)
      self.resetZebra_pv = PV(rz_pv)
      rz_reboot_pv = daq_utils.pvLookupDict["zebraRebootIOC"]
      logger.info('setting zebra reboot ioc PV: %s' % rz_reboot_pv)
      self.rebootZebraIOC_pv = PV(rz_reboot_pv)      
      self.zebraArmedPV = PV(daq_utils.pvLookupDict["zebraArmStatus"])
      self.zebraArmStateSignal.connect(self.processZebraArmState)
      self.zebraArmedPV.add_callback(self.zebraArmStateChangedCB)

      self.govRobotSeReachPV = PV(daq_utils.pvLookupDict["govRobotSeReach"])
      self.govRobotSeReachSignal.connect(self.processGovRobotSeReach)
      self.govRobotSeReachPV.add_callback(self.govRobotSeReachChangedCB)

      self.govRobotSaReachPV = PV(daq_utils.pvLookupDict["govRobotSaReach"])
      self.govRobotSaReachSignal.connect(self.processGovRobotSaReach)
      self.govRobotSaReachPV.add_callback(self.govRobotSaReachChangedCB)

      self.govRobotDaReachPV = PV(daq_utils.pvLookupDict["govRobotDaReach"])
      self.govRobotDaReachSignal.connect(self.processGovRobotDaReach)
      self.govRobotDaReachPV.add_callback(self.govRobotDaReachChangedCB)

      self.govRobotBlReachPV = PV(daq_utils.pvLookupDict["govRobotBlReach"])
      self.govRobotBlReachSignal.connect(self.processGovRobotBlReach)
      self.govRobotBlReachPV.add_callback(self.govRobotBlReachChangedCB)
      
      self.detectorMessagePV = PV(daq_utils.pvLookupDict["eigerStatMessage"])
      self.detMessageSignal.connect(self.processDetMessage)
      self.detectorMessagePV.add_callback(self.detMessageChangedCB)


      self.sampleFluxSignal.connect(self.processSampleFlux)
      self.sampleFluxPV.add_callback(self.sampleFluxChangedCB)
      
      self.stillModeStateSignal.connect(self.processStillModeState)
      self.stillModeStatePV.add_callback(self.stillModeStateChangedCB)      

      self.zebraPulsePV = PV(daq_utils.pvLookupDict["zebraPulseStatus"])
      self.zebraPulseStateSignal.connect(self.processZebraPulseState)
      self.zebraPulsePV.add_callback(self.zebraPulseStateChangedCB)

      self.zebraDownloadPV = PV(daq_utils.pvLookupDict["zebraDownloading"])
      self.zebraDownloadStateSignal.connect(self.processZebraDownloadState)
      self.zebraDownloadPV.add_callback(self.zebraDownloadStateChangedCB)

      self.zebraSentTriggerPV = PV(daq_utils.pvLookupDict["zebraSentTriggerStatus"])
      self.zebraSentTriggerStateSignal.connect(self.processZebraSentTriggerState)
      self.zebraSentTriggerPV.add_callback(self.zebraSentTriggerStateChangedCB)

      self.zebraReturnedTriggerPV = PV(daq_utils.pvLookupDict["zebraTriggerReturnStatus"])
      self.zebraReturnedTriggerStateSignal.connect(self.processZebraReturnedTriggerState)
      self.zebraReturnedTriggerPV.add_callback(self.zebraReturnedTriggerStateChangedCB)
      
      self.controlMaster_pv = PV(daq_utils.beamlineComm + "zinger_flag")
      self.controlMasterSignal.connect(self.processControlMaster)
      self.controlMaster_pv.add_callback(self.controlMasterChangedCB)

      self.beamCenterX_pv = PV(daq_utils.pvLookupDict["beamCenterX"])
      self.beamCenterY_pv = PV(daq_utils.pvLookupDict["beamCenterY"])      

      self.choochResultFlag_pv = PV(daq_utils.beamlineComm + "choochResultFlag")
      self.choochResultSignal.connect(self.processChoochResult)
      self.choochResultFlag_pv.add_callback(self.processChoochResultsCB)  
      self.xrecRasterFlag_pv = PV(daq_utils.beamlineComm + "xrecRasterFlag")
      self.xrecRasterFlag_pv.put("0")
      self.xrecRasterSignal.connect(self.displayXrecRaster)
      self.xrecRasterFlag_pv.add_callback(self.processXrecRasterCB)  
      self.message_string_pv = PV(daq_utils.beamlineComm + "message_string") 
      self.serverMessageSignal.connect(self.printServerMessage)
      self.message_string_pv.add_callback(self.serverMessageCB)  
      self.popup_message_string_pv = PV(daq_utils.beamlineComm + "gui_popup_message_string") 
      self.serverPopupMessageSignal.connect(self.popupServerMessage)
      self.popup_message_string_pv.add_callback(self.serverPopupMessageCB)  
      self.program_state_pv = PV(daq_utils.beamlineComm + "program_state") 
      self.programStateSignal.connect(self.colorProgramState)
      self.program_state_pv.add_callback(self.programStateCB)  
      self.pause_button_state_pv = PV(daq_utils.beamlineComm + "pause_button_state") 
      self.pauseButtonStateSignal.connect(self.changePauseButtonState)
      self.pause_button_state_pv.add_callback(self.pauseButtonStateCB)  

      self.energyChangeSignal.connect(self.processEnergyChange)
      self.energy_pv.add_callback(self.processEnergyChangeCB,motID="x")

      self.sampx_pv = PV(daq_utils.motor_dict["sampleX"]+".RBV")      
      self.sampMoveSignal.connect(self.processSampMove)
      self.sampx_pv.add_callback(self.processSampMoveCB,motID="x")
      self.sampy_pv = PV(daq_utils.motor_dict["sampleY"]+".RBV")
      self.sampy_pv.add_callback(self.processSampMoveCB,motID="y")
      self.sampz_pv = PV(daq_utils.motor_dict["sampleZ"]+".RBV")
      self.sampz_pv.add_callback(self.processSampMoveCB,motID="z")

      if (self.scannerType == "PI"):
        self.sampFineX_pv = PV(daq_utils.motor_dict["fineX"]+".RBV")
        self.sampFineX_pv.add_callback(self.processSampMoveCB,motID="fineX")
        self.sampFineY_pv = PV(daq_utils.motor_dict["fineY"]+".RBV")
        self.sampFineY_pv.add_callback(self.processSampMoveCB,motID="fineY")
        self.sampFineZ_pv = PV(daq_utils.motor_dict["fineZ"]+".RBV")
        self.sampFineZ_pv.add_callback(self.processSampMoveCB,motID="fineZ")
          
      
      self.omega_pv = PV(daq_utils.motor_dict["omega"] + ".VAL")
      self.omegaTweak_pv = PV(daq_utils.motor_dict["omega"] + ".RLV")
      self.sampyTweak_pv = PV(daq_utils.motor_dict["sampleY"] + ".RLV")
      self.sampzTweak_pv = PV(daq_utils.motor_dict["sampleZ"] + ".RLV")            
      self.omegaRBV_pv = PV(daq_utils.motor_dict["omega"] + ".RBV")
      self.omegaRBV_pv.add_callback(self.processSampMoveCB,motID="omega") #I think monitoring this allows for the textfield to monitor val and this to deal with the graphics. Else next line has two callbacks on same thing.
      self.photonShutterOpen_pv = PV(daq_utils.pvLookupDict["photonShutterOpen"])
      self.photonShutterClose_pv = PV(daq_utils.pvLookupDict["photonShutterClose"])      
      self.fastShutterRBV_pv = PV(daq_utils.motor_dict["fastShutter"] + ".RBV")
      self.fastShutterSignal.connect(self.processFastShutter)
      self.fastShutterRBV_pv.add_callback(self.shutterChangedCB)
      self.gripTempSignal.connect(self.processGripTemp)
      self.gripTemp_pv.add_callback(self.gripTempChangedCB)
      self.cryostreamTempSignal.connect(self.processCryostreamTemp)
      self.cryostreamTemp_pv.add_callback(self.cryostreamTempChangedCB)
      self.ringCurrentSignal.connect(self.processRingCurrent)      
      self.ringCurrent_pv.add_callback(self.ringCurrentChangedCB)
      self.beamAvailableSignal.connect(self.processBeamAvailable)      
      self.beamAvailable_pv.add_callback(self.beamAvailableChangedCB)
      self.sampleExposedSignal.connect(self.processSampleExposed)      
      self.sampleExposed_pv.add_callback(self.sampleExposedChangedCB)
      self.highMagCursorChangeSignal.connect(self.processHighMagCursorChange)
      self.highMagCursorX_pv.add_callback(self.processHighMagCursorChangeCB,ID="x")
      self.highMagCursorY_pv.add_callback(self.processHighMagCursorChangeCB,ID="y")      
      self.lowMagCursorChangeSignal.connect(self.processLowMagCursorChange)
      self.lowMagCursorX_pv.add_callback(self.processLowMagCursorChangeCB,ID="x")
      self.lowMagCursorY_pv.add_callback(self.processLowMagCursorChangeCB,ID="y")      
        

        

    def popupServerMessage(self,message_s):

      if (self.popUpMessageInit):
        self.popUpMessageInit = 0
        return        
      self.popupMessage.done(1)
      if (message_s == "killMessage"):
        return
      else:
        self.popupMessage.showMessage(message_s)


    def printServerMessage(self,message_s):
      if (self.textWindowMessageInit):
        self.textWindowMessageInit = 0
        return        
      logger.info(message_s)
      print(message_s)


    def colorProgramState(self,programState_s):
      if (programState_s.find("Ready") == -1):
        self.statusLabel.setColor("yellow")
      else:
        self.statusLabel.setColor("#99FF66")        

    def changePauseButtonState(self,buttonState_s):
      self.pauseQueueButton.setText(buttonState_s)
      if (buttonState_s.find("Pause") != -1):
        self.pauseQueueButton.setStyleSheet("background-color: None")                  
      else:
        self.pauseQueueButton.setStyleSheet("background-color: yellow")                    


    def controlEnabled(self):
      return (self.processID == abs(int(self.controlMaster_pv.get())) and self.controlMasterCheckBox.isChecked())
        
    def send_to_server(self,s):
      if (s == "lockControl"):
        self.controlMaster_pv.put(0-self.processID)
        return
      if (s == "unlockControl"):
        self.controlMaster_pv.put(self.processID)
        return
      if (self.controlEnabled()):

        time.sleep(.01)
        logger.info('send_to_server: %s' % s)
        self.comm_pv.put(s)
      else:
        self.popupServerMessage("You don't have control")
      


    def aux_send_to_server(self,s):
      if (self.controlEnabled()):
        time.sleep(.01)
        logger.info('aux_send_to_server: %s' % s)
        self.immediate_comm_pv.put(s)
      else:
        self.popupServerMessage("You don't have control")


def get_request_object_escan(reqObj, symbol, runNum, file_prefix, base_path, sampleName, containerID, samplePositionInContainer,
                             file_number_start, exposure_time, targetEnergy, steps, stepsize):
    reqObj["element"] = symbol
    reqObj["runNum"] = runNum
    reqObj["file_prefix"] = str(file_prefix)
    reqObj["basePath"] = str(base_path)
    reqObj["directory"] = str(base_path) + "/" + str(
        daq_utils.getVisitName()) + "/" + sampleName + "/" + str(runNum) + "/" + db_lib.getContainerNameByID(
        containerID) + "_" + str(samplePositionInContainer + 1) + "/"
    try:
        reqObj["file_number_start"] = int(file_number_start)
    except ValueError as e:
        logger.error('Problem with a value passed in - %s' % e)
        reqObj["file_number_start"] = 1
    reqObj["exposure_time"] = float(exposure_time)
    reqObj["protocol"] = "eScan"
    reqObj["scanEnergy"] = targetEnergy
    reqObj["runChooch"] = True  # just hardcode for now
    reqObj["steps"] = int(steps)
    reqObj["stepsize"] = int(stepsize)
    return reqObj

def main():
    daq_utils.init_environment()
    daq_utils.readPVDesc()    
    app = QtWidgets.QApplication(sys.argv)
    ex = ControlMain()
    sys.exit(app.exec_())

#skinner - I think Matt did a lot of what's below and I have no idea what it is. 
if __name__ == '__main__':
    if '-pc' in sys.argv or '-p' in sys.argv:
        logger.info('cProfile not working yet :(')
        #print 'starting cProfile profiler...'
        #import cProfile, pstats, io
        #pr = cProfile.Profile()
        #pr.enable()

    elif '-py' in sys.argv:
        logger.info('starting yappi profiler...')
        import yappi
        yappi.start(True)

    try:
        main()    

    finally:
        if '-pc' in sys.argv or '-p' in sys.argv:
            pass
            #pr.disable()
            #s = StringIO()
            #sortby = 'cumulative'
            #ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            #ps.print_stats()  # dies here, expected unicode, got string, need unicode io stream?
            #logger.info(s.getvalue())

        elif '-py' in sys.argv:
            # stop profiler and print results
            yappi.stop()
            yappi.get_func_stats().print_all()
            yappi.get_thread_stats().print_all()
            logger.info('memory usage: {0}'.format(yappi.get_mem_usage()))
