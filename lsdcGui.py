#!/opt/conda_envs/lsdc_dev/bin/python
"""
The GUI for the LSDC system
"""
import sys
import os
import string
import math
import urllib
from io import StringIO
from epics import PV
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import * 
from PyQt4.QtGui import * 
import db_lib
from QtEpicsMotorEntry import *
from QtEpicsMotorLabel import *
from QtEpicsPVLabel import *
from QtEpicsPVEntry import *
import cv2
from cv2 import *
from PIL import Image
import ImageQt
import daq_utils
import albulaUtils
import functools
from QPeriodicTable import *
from PyMca.QtBlissGraph import QtBlissGraph
from PyMca.McaAdvancedFit import McaAdvancedFit
from PyMca import ElementsInfo
from element_info import element_info 
import numpy as np
import _thread #TODO python document suggests using threading! make this chance once stable
import lsdcOlog
import daq_utils

import socket
hostname = socket.gethostname()
if hostname == 'xf17id1-ws4' or hostname == 'xf17id2-ws2':
    logging_file = 'lsdcGuiLog.txt'
elif hostname == 'xf17id1-ws2' or hostname == 'xf17id2-ws4':
    user = os.environ['USER']
    logging_file = '/home/%s/lsdcGuiLog.txt' % user
else:
    print('lsdcGui not being run on one of the "normal" workstations. log going into home directory of current user')
    user = os.environ['USER']
    logging_file = '/home/%s/lsdcGuiLog.txt' % user
import logging
from logging import handlers
logger = logging.getLogger()
logging.getLogger().setLevel(logging.INFO)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)
handler1 = handlers.RotatingFileHandler(logging_file, maxBytes=50000000)
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
  logger.error("lsdcGui ISPYB import error: %s" % e)
import raddoseLib

global sampleNameDict
sampleNameDict = {}

global containerDict
containerDict = {}


class SnapCommentDialog(QDialog):
    def __init__(self,parent = None):
        QDialog.__init__(self,parent)
        self.setWindowTitle("Snapshot Comment")
        self.setModal(False)
        vBoxColParams1 = QtGui.QVBoxLayout()
        hBoxColParams1 = QtGui.QHBoxLayout()
        self.textEdit = QtGui.QPlainTextEdit()
        vBoxColParams1.addWidget(self.textEdit)
        self.ologCheckBox = QCheckBox("Save to Olog")
        self.ologCheckBox.setChecked(False)
        vBoxColParams1.addWidget(self.ologCheckBox)        
        commentButton = QtGui.QPushButton("Add Comment")        
        commentButton.clicked.connect(self.commentCB)
        cancelButton = QtGui.QPushButton("Cancel")        
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

class RasterExploreDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setModal(False)
        self.setWindowTitle("Raster Explore")
        vBoxParams1 = QtGui.QVBoxLayout()
        hBoxParams1 = QtGui.QHBoxLayout()
        hBoxParams2 = QtGui.QHBoxLayout()
        hBoxParams3 = QtGui.QHBoxLayout()
        spotCountLabel = QtGui.QLabel('Spot Count:')
        spotCountLabel.setFixedWidth(120)
        self.spotCount_ledit = QtGui.QLabel()
        self.spotCount_ledit.setFixedWidth(60)
        hBoxParams1.addWidget(spotCountLabel)
        hBoxParams1.addWidget(self.spotCount_ledit)
        intensityLabel = QtGui.QLabel('Total Intensity:')
        intensityLabel.setFixedWidth(120)
        self.intensity_ledit = QtGui.QLabel()
        self.intensity_ledit.setFixedWidth(60)
        hBoxParams2.addWidget(intensityLabel)
        hBoxParams2.addWidget(self.intensity_ledit)
        resoLabel = QtGui.QLabel('Resolution:')
        resoLabel.setFixedWidth(120)
        self.reso_ledit = QtGui.QLabel()
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
        vBoxColParams1 = QtGui.QVBoxLayout()
        hBoxColParams0 = QtGui.QHBoxLayout()                
        hBoxColParams1 = QtGui.QHBoxLayout()        
        hBoxColParams2 = QtGui.QHBoxLayout()
        hBoxColParams3 = QtGui.QHBoxLayout()
        hBoxFastDP = QtGui.QHBoxLayout()
        hBoxSpotfinder = QtGui.QHBoxLayout()
        puckToDewarButton = QtGui.QPushButton("Puck to Dewar...")
        puckToDewarButton.clicked.connect(self.parent.puckToDewarCB)
        removePuckButton = QtGui.QPushButton("Remove Puck...")
        removePuckButton.clicked.connect(self.parent.removePuckCB)
        hBoxColParams0.addWidget(puckToDewarButton)
        hBoxColParams0.addWidget(removePuckButton )                        
        self.robotOnCheckBox = QCheckBox("Robot (On)")
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"robot_online") == 1):
          self.robotOnCheckBox.setChecked(True)
        else:
          self.robotOnCheckBox.setChecked(False)            
        self.robotOnCheckBox.stateChanged.connect(self.robotOnCheckCB)
        self.topViewCheckOnCheckBox = QCheckBox("TopViewCheck (On)")
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"topViewCheck") == 1):
          self.topViewCheckOnCheckBox.setChecked(True)
        else:
          self.topViewCheckOnCheckBox.setChecked(False)            
        self.topViewCheckOnCheckBox.stateChanged.connect(self.topViewOnCheckCB)
        self.queueCollectOnCheckBox = QCheckBox("Queue Collect")
        hBoxColParams1.addWidget(self.queueCollectOnCheckBox)
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"queueCollect") == 1):
          self.queueCollectOnCheckBox.setChecked(True)
        else:
          self.queueCollectOnCheckBox.setChecked(False)            
        self.queueCollectOnCheckBox.stateChanged.connect(self.queueCollectOnCheckCB)
        self.vertRasterOnCheckBox = QCheckBox("Vert. Raster")
        hBoxColParams1.addWidget(self.vertRasterOnCheckBox)        
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"vertRasterOn") == 1):
          self.vertRasterOnCheckBox.setChecked(True)
        else:
          self.vertRasterOnCheckBox.setChecked(False)            
        self.vertRasterOnCheckBox.stateChanged.connect(self.vertRasterOnCheckCB)
        self.procRasterOnCheckBox = QCheckBox("Process Raster")
        hBoxColParams1.addWidget(self.procRasterOnCheckBox)        
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterProcessFlag") == 1):
          self.procRasterOnCheckBox.setChecked(True)
        else:
          self.procRasterOnCheckBox.setChecked(False)            
        self.procRasterOnCheckBox.stateChanged.connect(self.procRasterOnCheckCB)
        self.guiRemoteOnCheckBox = QCheckBox("GUI Remote")
        hBoxColParams1.addWidget(self.guiRemoteOnCheckBox)        
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"omegaMonitorPV") == "VAL"):
          self.guiRemoteOnCheckBox.setChecked(True)
        else:
          self.guiRemoteOnCheckBox.setChecked(False)            
        self.guiRemoteOnCheckBox.stateChanged.connect(self.guiRemoteOnCheckCB)
        self.enableMountCheckBox = QCheckBox("Enable Mount")
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"mountEnabled") == 1):
          self.enableMountCheckBox.setChecked(True)
        else:
          self.enableMountCheckBox.setChecked(False)            
        self.enableMountCheckBox.stateChanged.connect(self.enableMountCheckCB)
        self.unmountColdButton = QtGui.QPushButton("Unmount Cold")
        self.unmountColdButton.clicked.connect(self.unmountColdCB)
        self.openPort1Button = QtGui.QPushButton("Open Port 1")
        self.openPort1Button.clicked.connect(self.openPort1CB)
        self.closePortsButton = QtGui.QPushButton("Close Ports")
        self.closePortsButton.clicked.connect(self.closePortsCB)
        self.warmupButton = QtGui.QPushButton("Dry Gripper")        
        self.warmupButton.clicked.connect(self.parent.dryGripperCB)
        self.cooldownButton = QtGui.QPushButton("Cooldown Gripper")        
        self.cooldownButton.clicked.connect(self.parent.cooldownGripperCB)
        self.parkButton = QtGui.QPushButton("Park Gripper")        
        self.parkButton.clicked.connect(self.parent.parkGripperCB)
        self.homePinsButton = QtGui.QPushButton("Home Pins")
        self.homePinsButton.clicked.connect(self.homePinsCB)
        self.clearMountedSampleButton = QtGui.QPushButton("Clear Mounted Sample")
        self.clearMountedSampleButton.clicked.connect(self.clearMountedSampleCB)
        hBoxColParams2.addWidget(self.openPort1Button)
        hBoxColParams2.addWidget(self.closePortsButton)        
        hBoxColParams2.addWidget(self.unmountColdButton)
        hBoxColParams2.addWidget(self.warmupButton)
        hBoxColParams2.addWidget(self.cooldownButton)
        hBoxColParams2.addWidget(self.parkButton)                        
        hBoxColParams2.addWidget(self.clearMountedSampleButton)
        hBoxColParams1.addWidget(self.homePinsButton)        
        self.setFastDPNodesButton = QtGui.QPushButton("Set FastDP Nodes")
        self.setFastDPNodesButton.clicked.connect(self.setFastDPNodesCB)
        hBoxFastDP.addWidget(self.setFastDPNodesButton)        
        self.fastDPNodeEntryList = []
        nodeList = self.getFastDPNodeList()        
        for i in range (0,self.fastDPNodeCount):
          self.fastDPNodeEntryList.append(QtGui.QLineEdit())
          self.fastDPNodeEntryList[i].setFixedWidth(30)
          self.fastDPNodeEntryList[i].setText(str(nodeList[i]))
          hBoxFastDP.addWidget(self.fastDPNodeEntryList[i])
        self.setBeamcenterButton = QtGui.QPushButton("Set Beamcenter")
        self.setBeamcenterButton.clicked.connect(self.setBeamcenterCB)
        hBoxFastDP.addWidget(self.setBeamcenterButton)
        self.beamcenterX_ledit =  QtGui.QLineEdit()
        self.beamcenterX_ledit.setText(str(self.parent.beamCenterX_pv.get()))        
        self.beamcenterY_ledit =  QtGui.QLineEdit()
        self.beamcenterY_ledit.setText(str(self.parent.beamCenterY_pv.get()))
        hBoxFastDP.addWidget(self.beamcenterX_ledit)
        hBoxFastDP.addWidget(self.beamcenterY_ledit)                
        self.setSpotNodesButton = QtGui.QPushButton("Set Spotfinder Nodes")
        self.setSpotNodesButton.clicked.connect(self.setSpotNodesCB)
        self.lockGuiButton = QtGui.QPushButton("Lock")
        self.lockGuiButton.clicked.connect(self.lockGuiCB)
        self.unLockGuiButton = QtGui.QPushButton("unLock")
        self.unLockGuiButton.clicked.connect(self.unLockGuiCB)
        hBoxSpotfinder.addWidget(self.lockGuiButton)
        hBoxSpotfinder.addWidget(self.unLockGuiButton)                        
        hBoxSpotfinder.addWidget(self.setSpotNodesButton)        
        self.spotNodeEntryList = []
        nodeList = self.getSpotNodeList()        
        for i in range (0,self.spotNodeCount):
          self.spotNodeEntryList.append(QtGui.QLineEdit())
          self.spotNodeEntryList[i].setFixedWidth(30)
          self.spotNodeEntryList[i].setText(str(nodeList[i]))          
          hBoxSpotfinder.addWidget(self.spotNodeEntryList[i])
        robotGB = QtGui.QGroupBox()
        robotGB.setTitle("Robot")
        hBoxRobot1 = QtGui.QHBoxLayout()
        vBoxRobot1 = QtGui.QVBoxLayout()
        self.recoverRobotButton = QtGui.QPushButton("Recover Robot")
        self.recoverRobotButton.clicked.connect(self.recoverRobotCB)
        self.rebootEMBLButton = QtGui.QPushButton("Reboot EMBL")
        self.rebootEMBLButton.clicked.connect(self.rebootEMBL_CB)
        self.restartEMBLButton = QtGui.QPushButton("Start EMBL")
        self.restartEMBLButton.clicked.connect(self.restartEMBL_CB)
        self.openGripperButton = QtGui.QPushButton("Open Gripper")
        self.openGripperButton.clicked.connect(self.openGripper_CB)
        self.closeGripperButton = QtGui.QPushButton("Close Gripper")
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
        nodeList.append(int(db_lib.getBeamlineConfigParam(daq_utils.beamline,"spotNode"+str(i+1)).split('-')[1]))
      return nodeList
        
        
    def getFastDPNodeList(self):
      nodeList = []
      for i in range (0,self.fastDPNodeCount):
        nodeList.append(int(db_lib.getBeamlineConfigParam(daq_utils.beamline,"fastDPNode"+str(i+1)).split('-')[1]))
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
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"robot_online",1)
      else:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"robot_online",0)

    def topViewOnCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"topViewCheck",1)
      else:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"topViewCheck",0)
        
    def vertRasterOnCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"vertRasterOn",1)
      else:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"vertRasterOn",0)

    def procRasterOnCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterProcessFlag",1)
      else:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterProcessFlag",0)

    def guiRemoteOnCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"omegaMonitorPV","VAL")
      else:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"omegaMonitorPV","RBV")
        
    def queueCollectOnCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"queueCollect",1)
      else:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"queueCollect",0)

    def enableMountCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"mountEnabled",1)
      else:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"mountEnabled",0)

    def screenDefaultsCancelCB(self):
      self.hide()

    def screenDefaultsOKCB(self):
      self.hide()
        

class UserScreenDialog(QFrame):  
    def __init__(self,parent = None):
        self.parent=parent
        QFrame.__init__(self)
        self.setWindowTitle("User Extras")        
        vBoxColParams1 = QtGui.QVBoxLayout()
        hBoxColParams1 = QtGui.QHBoxLayout()        
        hBoxColParams2 = QtGui.QHBoxLayout()
        hBoxColParams25 = QtGui.QHBoxLayout()        
        hBoxColParams3 = QtGui.QHBoxLayout()        
        govLabel = QtGui.QLabel('Set Governor State:')        
        self.SEbutton = QtGui.QPushButton("SE")
        self.SEbutton.clicked.connect(self.SEgovCB)
        self.SAbutton = QtGui.QPushButton("SA")
        self.SAbutton.clicked.connect(self.SAgovCB)
        self.DAbutton = QtGui.QPushButton("DA")
        self.DAbutton.clicked.connect(self.DAgovCB)
        self.BLbutton = QtGui.QPushButton("BL")
        self.BLbutton.clicked.connect(self.BLgovCB)
        hBoxColParams1.addWidget(govLabel)
        hBoxColParams1.addWidget(self.SEbutton)
        hBoxColParams1.addWidget(self.SAbutton)
        hBoxColParams1.addWidget(self.DAbutton)
        hBoxColParams1.addWidget(self.BLbutton)        
        govLabel2 = QtGui.QLabel('Current Governor State:')                
        self.governorMessage = QtEpicsPVLabel(daq_utils.pvLookupDict["governorMessage"],self,140,highlight_on_change=False)
        hBoxColParams2.addWidget(govLabel2)
        hBoxColParams2.addWidget(self.governorMessage.getEntry())
        
        self.openShutterButton = QtGui.QPushButton("Open Photon Shutter")
        self.openShutterButton.clicked.connect(self.parent.openPhotonShutterCB)
        hBoxColParams25.addWidget(self.openShutterButton)        
        robotGB = QtGui.QGroupBox()
        robotGB.setTitle("Robot")

        self.unmountColdButton = QtGui.QPushButton("Unmount Cold")
        self.unmountColdButton.clicked.connect(self.unmountColdCB)        
        self.testRobotButton = QtGui.QPushButton("Test Robot")
        self.testRobotButton.clicked.connect(self.testRobotCB)        
        self.recoverRobotButton = QtGui.QPushButton("Recover Robot")
        self.recoverRobotButton.clicked.connect(self.recoverRobotCB)        
        self.dryGripperButton = QtGui.QPushButton("Dry Gripper")
        self.dryGripperButton.clicked.connect(self.dryGripperCB)        

        hBoxColParams3.addWidget(self.unmountColdButton)
        hBoxColParams3.addWidget(self.testRobotButton)
        hBoxColParams3.addWidget(self.recoverRobotButton)        
        hBoxColParams3.addWidget(self.dryGripperButton)
        robotGB.setLayout(hBoxColParams3)

        zebraGB = QtGui.QGroupBox()
        detGB = QtGui.QGroupBox()        
        zebraGB.setTitle("Zebra (Timing)")
        detGB.setTitle("Eiger Detector")
        hBoxDet1 = QtGui.QHBoxLayout()
        hBoxDet2 = QtGui.QHBoxLayout()        
        vBoxDet1 = QtGui.QVBoxLayout()
        self.stopDetButton = QtGui.QPushButton("Stop")
        self.stopDetButton.clicked.connect(self.stopDetCB)
        self.rebootDetIocButton = QtGui.QPushButton("Reboot Det IOC")
        self.rebootDetIocButton.clicked.connect(self.rebootDetIocCB)
        detStatLabel = QtGui.QLabel('Detector Status:')
        self.detMessage_ledit = QtGui.QLabel()
        hBoxDet1.addWidget(self.stopDetButton)
        hBoxDet1.addWidget(self.rebootDetIocButton)
        hBoxDet2.addWidget(detStatLabel)
        hBoxDet2.addWidget(self.detMessage_ledit)

        beamGB = QtGui.QGroupBox()
        beamGB.setTitle("Beam")
        hBoxBeam1 = QtGui.QHBoxLayout()
        hBoxBeam2 = QtGui.QHBoxLayout()
        hBoxBeam3 = QtGui.QHBoxLayout()        
        vBoxBeam = QtGui.QVBoxLayout()
        if (daq_utils.beamline == "fmx"):
          slit1XLabel = QtGui.QLabel('Slit 1 X Gap:')
          slit1XLabel.setAlignment(QtCore.Qt.AlignCenter)         
          slit1XRBLabel = QtGui.QLabel("Readback:")
          self.slit1XRBVLabel = QtEpicsPVLabel(daq_utils.motor_dict["slit1XGap"] + ".RBV",self,70) 
          slit1XSPLabel = QtGui.QLabel("SetPoint:")
          self.slit1XMotor_ledit = QtGui.QLineEdit()
          self.slit1XMotor_ledit.returnPressed.connect(self.setSlit1XCB)
          self.slit1XMotor_ledit.setText(str(self.parent.slit1XGapSP_pv.get()))

          slit1YLabel = QtGui.QLabel('Slit 1 Y Gap:')
          slit1YLabel.setAlignment(QtCore.Qt.AlignCenter)         
          slit1YRBLabel = QtGui.QLabel("Readback:")
          self.slit1YRBVLabel = QtEpicsPVLabel(daq_utils.motor_dict["slit1YGap"] + ".RBV",self,70) 
          slit1YSPLabel = QtGui.QLabel("SetPoint:")
          self.slit1YMotor_ledit = QtGui.QLineEdit()
          self.slit1YMotor_ledit.setText(str(self.parent.slit1YGapSP_pv.get()))          
          self.slit1YMotor_ledit.returnPressed.connect(self.setSlit1YCB)
        
        sampleFluxLabelDesc = QtGui.QLabel("Sample Flux:")
        sampleFluxLabelDesc.setFixedWidth(80)
        self.sampleFluxLabel = QtGui.QLabel()
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
        hBoxColParams4 = QtGui.QHBoxLayout()
        vBoxZebraParams4 = QtGui.QVBoxLayout()        
        self.resetZebraButton = QtGui.QPushButton("Reset Zebra")
        self.resetZebraButton.clicked.connect(self.resetZebraCB)
        self.rebootZebraButton = QtGui.QPushButton("Reboot Zebra IOC")
        self.rebootZebraButton.clicked.connect(self.rebootZebraIOC_CB)
        hBoxColParams5 = QtGui.QHBoxLayout()
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
      self.parent.stopDet_pv.put(1)

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
      

class ScreenDefaultsDialog(QDialog):
    def __init__(self,parent = None):
        QDialog.__init__(self,parent)
        self.parent=parent        
        self.setModal(False)
        self.setWindowTitle("Raster Params")        
        vBoxColParams1 = QtGui.QVBoxLayout()
        hBoxColParams2 = QtGui.QHBoxLayout()
        colRangeLabel = QtGui.QLabel('Oscillation Width:')
        colRangeLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.osc_range_ledit = QtGui.QLineEdit() # note, this is for rastering! same name used for data collections
        self.osc_range_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterDefaultWidth")))
        self.osc_range_ledit.returnPressed.connect(self.screenDefaultsOKCB)                        
        colExptimeLabel = QtGui.QLabel('ExposureTime:')
        colExptimeLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.exp_time_ledit = QtGui.QLineEdit()
        self.exp_time_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterDefaultTime")))
        self.exp_time_ledit.returnPressed.connect(self.screenDefaultsOKCB)                
        colTransLabel = QtGui.QLabel('Transmission (0.0-1.0):')
        colTransLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.trans_ledit = QtGui.QLineEdit()
        self.trans_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterDefaultTrans")))
        self.trans_ledit.returnPressed.connect(self.screenDefaultsOKCB)                
        colMinSpotLabel = QtGui.QLabel('Min Spot Size:')
        colMinSpotLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.minSpot_ledit = QtGui.QLineEdit()
        self.minSpot_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterDefaultMinSpotSize")))
        self.minSpot_ledit.returnPressed.connect(self.screenDefaultsOKCB)                
        hBoxColParams2.addWidget(colRangeLabel)
        hBoxColParams2.addWidget(self.osc_range_ledit)
        hBoxColParams2.addWidget(colExptimeLabel)
        hBoxColParams2.addWidget(self.exp_time_ledit)
        hBoxColParams2.addWidget(colTransLabel)
        hBoxColParams2.addWidget(self.trans_ledit)
        hBoxColParams2.addWidget(colMinSpotLabel)
        hBoxColParams2.addWidget(self.minSpot_ledit)
        self.hBoxRasterLayout2 = QtGui.QHBoxLayout()
        rasterTuneLabel = QtGui.QLabel('Raster\nTuning')
        self.rasterResoCheckBox = QCheckBox("Constrain Resolution")
        self.rasterResoCheckBox.stateChanged.connect(self.rasterResoCheckCB)
        rasterLowResLabel  = QtGui.QLabel('LowRes:')
        self.rasterLowRes = QtGui.QLineEdit()
        self.rasterLowRes.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterTuneLowRes")))
        self.rasterLowRes.returnPressed.connect(self.screenDefaultsOKCB)                
        rasterHighResLabel  = QtGui.QLabel('HighRes:')
        self.rasterHighRes = QtGui.QLineEdit()
        self.rasterHighRes.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterTuneHighRes")))
        self.rasterHighRes.returnPressed.connect(self.screenDefaultsOKCB)                
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterTuneResoFlag") == 1):
          resoFlag = True
        else:
          resoFlag = False
          self.rasterHighRes.setEnabled(False)
          self.rasterLowRes.setEnabled(False)                    
        self.rasterResoCheckBox.setChecked(resoFlag)
        self.rasterIceRingCheckBox = QCheckBox("Ice Ring")
        self.rasterIceRingCheckBox.setChecked(False)
        self.rasterIceRingCheckBox.stateChanged.connect(self.rasterIceRingCheckCB)        
        self.rasterIceRingWidth = QtGui.QLineEdit()
        self.rasterIceRingWidth.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterTuneIceRingWidth")))
        self.rasterIceRingWidth.returnPressed.connect(self.screenDefaultsOKCB)                
        self.rasterIceRingWidth.setEnabled(False)
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterTuneIceRingFlag") == 1):
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

        self.hBoxRasterLayout3 = QtGui.QHBoxLayout()
        self.rasterThreshCheckBox = QCheckBox("Tune Threshold")
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterThreshFlag") == 1):
          threshFlag = True
        else:
          threshFlag = False
        self.rasterThreshCheckBox.setChecked(threshFlag)
        self.rasterThreshCheckBox.stateChanged.connect(self.rasterThreshCheckCB)
        
        rasterThreshKernSizeLabel =  QtGui.QLabel('KernelSize')
        self.rasterThreshKernSize = QtGui.QLineEdit()
        self.rasterThreshKernSize.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterThreshKernSize")))
        self.rasterThreshKernSize.returnPressed.connect(self.screenDefaultsOKCB)                
        rasterThreshSigBckLabel =  QtGui.QLabel('SigmaBkrnd')        
        self.rasterThreshSigBckrnd = QtGui.QLineEdit()
        self.rasterThreshSigBckrnd.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterThreshSigBckrnd")))
        self.rasterThreshSigBckrnd.returnPressed.connect(self.screenDefaultsOKCB)                
        rasterThreshSigStrongLabel =  QtGui.QLabel('SigmaStrong')                
        self.rasterThreshSigStrong = QtGui.QLineEdit()
        self.rasterThreshSigStrong.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterThreshSigStrong")))
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
        reprocessRasterButton = QtGui.QPushButton("ReProcessRaster") 
        reprocessRasterButton.clicked.connect(self.reprocessRasterRequestCB)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Apply | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.buttons()[1].clicked.connect(self.screenDefaultsOKCB)
        self.buttons.buttons()[0].clicked.connect(self.screenDefaultsCancelCB)
        vBoxColParams1.addLayout(hBoxColParams2)
        vBoxColParams1.addLayout(self.hBoxRasterLayout2)
        vBoxColParams1.addLayout(self.hBoxRasterLayout3)
        vBoxColParams1.addWidget(reprocessRasterButton)                        
        vBoxColParams1.addWidget(self.buttons)
        self.setLayout(vBoxColParams1)

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

    def screenDefaultsOKCB(self):
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterDefaultWidth",float(self.osc_range_ledit.text()))
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterDefaultTime",float(self.exp_time_ledit.text()))
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterDefaultTrans",float(self.trans_ledit.text()))
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterDefaultMinSpotSize",float(self.minSpot_ledit.text()))            
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterTuneLowRes",float(self.rasterLowRes.text()))
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterTuneHighRes",float(self.rasterHighRes.text()))
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterTuneIceRingWidth",float(self.rasterIceRingWidth.text()))
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterThreshKernSize",float(self.rasterThreshKernSize.text()))
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterThreshSigBckrnd",float(self.rasterThreshSigBckrnd.text()))
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterThreshSigStrong",float(self.rasterThreshSigStrong.text()))                  
      if (self.rasterIceRingCheckBox.isChecked()):
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterTuneIceRingFlag",1)
      else:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterTuneIceRingFlag",0)          
      if (self.rasterResoCheckBox.isChecked()):
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterTuneResoFlag",1)
      else:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterTuneResoFlag",0)          
    
    def rasterIceRingCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        self.rasterIceRingWidth.setEnabled(True)        
      else:
        self.rasterIceRingWidth.setEnabled(False)          

    def rasterResoCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterTuneResoFlag",1)        
        self.rasterLowRes.setEnabled(True)
        self.rasterHighRes.setEnabled(True)                
      else:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterTuneResoFlag",0)                
        self.rasterLowRes.setEnabled(False)
        self.rasterHighRes.setEnabled(False)                

    def rasterThreshCheckCB(self,state):
      if state == QtCore.Qt.Checked:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterThreshFlag",1)
        self.rasterThreshKernSize.setEnabled(True)
        self.rasterThreshSigBckrnd.setEnabled(True)
        self.rasterThreshSigStrong.setEnabled(True)                        
      else:
        db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterThreshFlag",0)        
        self.rasterThreshKernSize.setEnabled(False)
        self.rasterThreshSigBckrnd.setEnabled(False)
        self.rasterThreshSigStrong.setEnabled(False)                        


class PuckDialog(QtGui.QDialog):
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
        labels = QtCore.QStringList(("Name"))
        self.model.setHorizontalHeaderLabels(labels)
        for i in range(len(data)):
            name = QtGui.QStandardItem(data[i])
            self.model.appendRow(name)


    def initUI(self):
        self.tv = QtGui.QListView(self)
        self.tv.setModel(self.model)
        QtCore.QObject.connect(self.tv, QtCore.SIGNAL("doubleClicked (QModelIndex)"),self.containerOKCB)
        behavior = QtGui.QAbstractItemView.SelectRows
        self.tv.setSelectionBehavior(behavior)
        
        self.label = QtGui.QLabel(self)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.buttons()[0].clicked.connect(self.containerOKCB)
        self.buttons.buttons()[1].clicked.connect(self.containerCancelCB)
        layout = QtGui.QVBoxLayout()
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


class DewarDialog(QtGui.QDialog):
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
        layout = QtGui.QVBoxLayout()
        headerLabelLayout = QtGui.QHBoxLayout()
        aLabel = QtGui.QLabel("A")
        aLabel.setFixedWidth(15)
        headerLabelLayout.addWidget(aLabel)
        bLabel = QtGui.QLabel("B")
        bLabel.setFixedWidth(10)
        headerLabelLayout.addWidget(bLabel)
        cLabel = QtGui.QLabel("C")
        cLabel.setFixedWidth(10)
        headerLabelLayout.addWidget(cLabel)
        layout.addLayout(headerLabelLayout)
        self.allButtonList = [None]*(self.dewarSectors*self.pucksPerDewarSector)
        for i in range (0,self.dewarSectors):
          rowLayout = QtGui.QHBoxLayout()
          numLabel = QtGui.QLabel(str(i+1))
          rowLayout.addWidget(numLabel)
          for j in range (0,self.pucksPerDewarSector):
            dataIndex = (i*self.pucksPerDewarSector)+j            
            self.allButtonList[dataIndex] = QtGui.QPushButton((str(self.data[dataIndex])))
            self.allButtonList[dataIndex].clicked.connect(functools.partial(self.on_button,str(dataIndex)))
            rowLayout.addWidget(self.allButtonList[dataIndex])
          layout.addLayout(rowLayout)
        cancelButton = QtGui.QPushButton("Done")        
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


class DewarTree(QtGui.QTreeView):
    def __init__(self, parent=None):
        super(DewarTree, self).__init__(parent)
        self.pucksPerDewarSector = 3
        self.dewarSectors = 8
        self.parent=parent
        self.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
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
          item = QtGui.QStandardItem(QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"), QtCore.QString(index_s + " " + puckName))
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
                item = QtGui.QStandardItem(QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"), QtCore.QString(position_s))
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
                  if not (sampleRequestList[k]["request_obj"].has_key("protocol")):
                    continue
                  col_item = QtGui.QStandardItem(QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"), QtCore.QString(sampleRequestList[k]["request_obj"]["file_prefix"]+"_"+sampleRequestList[k]["request_obj"]["protocol"]))
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
                item = QtGui.QStandardItem(QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"), QtCore.QString(position_s))
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
          nodeString = QtCore.QString(str(db_lib.getSampleNamebyID(requestedSampleList[i])))
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
              col_item = QtGui.QStandardItem(QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"), QtCore.QString(self.orderedRequests[k]["request_obj"]["file_prefix"]+"_"+self.orderedRequests[k]["request_obj"]["protocol"]))
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
        reqID = str(item.data(32).toString())
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
        itemData = str(item.data(32).toString())
        itemDataType = str(item.data(33).toString())
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
        itemData = str(item.data(32).toString())
        itemDataType = str(item.data(33).toString())
        if (itemDataType == "request"): 
          selectedSampleRequest = db_lib.getRequestByID(itemData)
          db_lib.updatePriority(itemData,0)
      self.parent.treeChanged_pv.put(1)


    def confirmDelete(self):
      quit_msg = "Are you sure you want to delete all requests?"
      self.parent.timerHutch.stop()
      self.parent.timerSample.stop()      
      reply = QtGui.QMessageBox.question(self, 'Message',quit_msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
      self.parent.timerSample.start(0)            
      self.parent.timerHutch.start(500)      
      if reply == QtGui.QMessageBox.Yes:
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
        itemData = str(item.data(32).toString())
        itemDataType = str(item.data(33).toString())
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



class DataLocInfo(QtGui.QGroupBox):

    def __init__(self,parent=None):
        QGroupBox.__init__(self,parent)
        self.parent = parent
        self.setTitle("Data Location")
        self.vBoxDPathParams1 = QtGui.QVBoxLayout()
        self.hBoxDPathParams1 = QtGui.QHBoxLayout()
        self.basePathLabel = QtGui.QLabel('Base Path:')
        self.base_path_ledit = QtGui.QLineEdit() #leave editable for now
        self.base_path_ledit.setText(os.getcwd())
        self.base_path_ledit.textChanged[str].connect(self.basePathTextChanged)
        self.browseBasePathButton = QtGui.QPushButton("Browse...") 
        self.browseBasePathButton.clicked.connect(self.parent.popBaseDirectoryDialogCB)
        self.hBoxDPathParams1.addWidget(self.basePathLabel)
        self.hBoxDPathParams1.addWidget(self.base_path_ledit)
        self.hBoxDPathParams1.addWidget(self.browseBasePathButton)
        self.hBoxDPathParams2 = QtGui.QHBoxLayout()
        self.dataPrefixLabel = QtGui.QLabel('Data Prefix:\n(40 Char Limit)')
        self.prefix_ledit = QtGui.QLineEdit()
        self.prefix_ledit.textChanged[str].connect(self.prefixTextChanged)
        self.hBoxDPathParams2.addWidget(self.dataPrefixLabel)
        self.hBoxDPathParams2.addWidget(self.prefix_ledit)
        self.dataNumstartLabel = QtGui.QLabel('File Number Start:')
        self.file_numstart_ledit = QtGui.QLineEdit()
        self.file_numstart_ledit.setFixedWidth(50)
        self.hBoxDPathParams3 = QtGui.QHBoxLayout()
        self.dataPathLabel = QtGui.QLabel('Data Path:')
        self.dataPath_ledit = QtGui.QLineEdit()
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
      runNum = db_lib.getSampleRequestCount(self.parent.selectedSampleID)
      (puckPosition,samplePositionInContainer,containerID) = db_lib.getCoordsfromSampleID(daq_utils.beamline,self.parent.selectedSampleID)
      self.setDataPath_ledit(self.base_path_ledit.text()+"/"+ str(daq_utils.getVisitName()) + "/"+prefix+"/"+str(runNum+1)+"/"+db_lib.getContainerNameByID(containerID)+"_"+str(samplePositionInContainer+1)+"/")      

    def setFileNumstart_ledit(self,s):
      self.file_numstart_ledit.setText(s)

    def setFilePrefix_ledit(self,s):
      self.prefix_ledit.setText(s)

    def setBasePath_ledit(self,s):
      self.base_path_ledit.setText(s)

    def setDataPath_ledit(self,s):
      self.dataPath_ledit.setText(s)



class RasterCell(QtGui.QGraphicsRectItem):

    def __init__(self,x,y,w,h,topParent,scene):
      super(rasterCell,self).__init__(x,y,w,h,None,scene)
      self.topParent = topParent
      self.setAcceptHoverEvents(True)

    def mousePressEvent(self, e):
      if (self.topParent.vidActionRasterExploreRadio.isChecked()):
        if (self.data(0) != None):
          spotcount = self.data(0).toInt()[0]
          filename = self.data(1).toString()
          d_min = self.data(2).toDouble()[0]
          intensity = self.data(3).toInt()[0]
          if (self.topParent.albulaDispCheckBox.isChecked()):
            if (str(self.data(1).toString()) != "empty"):
              albulaUtils.albulaDispFile(str(self.data(1).toString()))
          if not (self.topParent.RasterExploreDialog.isVisible()):
            self.topParent.RasterExploreDialog.show()
          self.topParent.RasterExploreDialog.setSpotCount(spotcount)
          self.topParent.RasterExploreDialog.setTotalIntensity(intensity)
          self.topParent.RasterExploreDialog.setResolution(d_min)
          groupList = self.group().childItems()
          for i in range (0,len(groupList)):
            groupList[i].setPen(self.topParent.redPen)
          self.setPen(self.topParent.yellowPen)
                                              
      else:
        super(rasterCell, self).mousePressEvent(e)


    def hoverEnterEvent(self, e):
      if (self.data(0) != None):
        spotcount = self.data(0).toInt()[0]
        d_min = self.data(2).toDouble()[0]
        intensity = self.data(3).toInt()[0]
        if not (self.topParent.RasterExploreDialog.isVisible()):
          self.topParent.RasterExploreDialog.show()
        self.topParent.RasterExploreDialog.setSpotCount(spotcount)
        self.topParent.RasterExploreDialog.setTotalIntensity(intensity)
        self.topParent.RasterExploreDialog.setResolution(d_min)



class RasterGroup(QtGui.QGraphicsItemGroup):
    def __init__(self,parent = None):
        super(RasterGroup, self).__init__()
        self.parent=parent
        self.setHandlesChildEvents(False)


    def mousePressEvent(self, e):
      super(RasterGroup, self).mousePressEvent(e)
      logger.info("mouse pressed on group")
      for i in range(len(self.parent.rasterList)):
        if (self.parent.rasterList[i] != None):
          if (self.parent.rasterList[i]["graphicsItem"].isSelected()):
            logger.info("found selected raster")
            self.parent.SelectedItemData = self.parent.rasterList[i]["uid"]
            self.parent.treeChanged_pv.put(1)


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



class ControlMain(QtGui.QMainWindow):
#1/13/15 - are these necessary?
    Signal = QtCore.pyqtSignal()
    refreshTreeSignal = QtCore.pyqtSignal()
    serverMessageSignal = QtCore.pyqtSignal()
    serverPopupMessageSignal = QtCore.pyqtSignal()
    programStateSignal = QtCore.pyqtSignal()
    pauseButtonStateSignal = QtCore.pyqtSignal()    

    
    def __init__(self):
        super(ControlMain, self).__init__()
        self.SelectedItemData = "" #attempt to know what row is selected
        self.popUpMessageInit = 1 # I hate these next two, but I don't want to catch old messages. Fix later, maybe.
        self.textWindowMessageInit = 1
        self.processID = os.getpid()
        self.popupMessage = QtGui.QErrorMessage(self)
        self.popupMessage.setStyleSheet("background-color: red")
        self.popupMessage.setModal(False)
        self.groupName = "skinner"
        self.scannerType = db_lib.getBeamlineConfigParam(daq_utils.beamline,"scannerType")
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

    def initVideo4(self,frequency):
      self.captureHighMagZoom=cv2.VideoCapture(daq_utils.highMagZoomCamURL)
      

    def initVideo3(self,frequency):
      self.captureLowMagZoom=cv2.VideoCapture(daq_utils.lowMagZoomCamURL)

            
    def createSampleTab(self):

        sampleTab= QtGui.QWidget()      
        splitter1 = QtGui.QSplitter(Qt.Horizontal)
        vBoxlayout= QtGui.QVBoxLayout()
        self.dewarTreeFrame = QFrame()
        vBoxDFlayout= QtGui.QVBoxLayout()
        self.selectedSampleRequest = {}
        self.selectedSampleID = ""
        self.dewarTree   = DewarTree(self)
        QtCore.QObject.connect(self.dewarTree, QtCore.SIGNAL("clicked (QModelIndex)"),self.row_clicked)
        treeSelectBehavior = QtGui.QAbstractItemView.SelectItems
        treeSelectMode = QtGui.QAbstractItemView.ExtendedSelection
        self.dewarTree.setSelectionMode(treeSelectMode)
        self.dewarTree.setSelectionBehavior(treeSelectBehavior)
        hBoxRadioLayout1= QtGui.QHBoxLayout()   
        self.viewRadioGroup=QtGui.QButtonGroup()
        self.priorityViewRadio = QtGui.QRadioButton("PriorityView")
        self.priorityViewRadio.toggled.connect(functools.partial(self.dewarViewToggledCB,"priorityView"))
        self.viewRadioGroup.addButton(self.priorityViewRadio)
        self.dewarViewRadio = QtGui.QRadioButton("DewarView")
        self.dewarViewRadio.setChecked(True)        
        self.dewarViewRadio.toggled.connect(functools.partial(self.dewarViewToggledCB,"dewarView"))
        hBoxRadioLayout1.addWidget(self.dewarViewRadio)        
        hBoxRadioLayout1.addWidget(self.priorityViewRadio)
        self.viewRadioGroup.addButton(self.dewarViewRadio)
        vBoxDFlayout.addLayout(hBoxRadioLayout1)
        vBoxDFlayout.addWidget(self.dewarTree)
        queueSelectedButton = QtGui.QPushButton("Queue All Selected")        
        queueSelectedButton.clicked.connect(self.dewarTree.queueAllSelectedCB)
        deQueueSelectedButton = QtGui.QPushButton("deQueue All Selected")        
        deQueueSelectedButton.clicked.connect(self.dewarTree.deQueueAllSelectedCB)
        runQueueButton = QtGui.QPushButton("Collect Queue")
        runQueueButton.setStyleSheet("background-color: yellow")
        runQueueButton.clicked.connect(self.collectQueueCB)
        stopRunButton = QtGui.QPushButton("Stop Collection")
        stopRunButton.setStyleSheet("background-color: red")
        stopRunButton.clicked.connect(self.stopRunCB) #immediate stop everything
        puckToDewarButton = QtGui.QPushButton("Puck to Dewar...")        
        mountSampleButton = QtGui.QPushButton("Mount Sample")        
        mountSampleButton.clicked.connect(self.mountSampleCB)
        unmountSampleButton = QtGui.QPushButton("Unmount Sample")        
        unmountSampleButton.clicked.connect(self.unmountSampleCB)
        puckToDewarButton.clicked.connect(self.puckToDewarCB)
        removePuckButton = QtGui.QPushButton("Remove Puck...")        
        removePuckButton.clicked.connect(self.removePuckCB)
        expandAllButton = QtGui.QPushButton("Expand All")        
        expandAllButton.clicked.connect(self.dewarTree.expandAllCB)
        collapseAllButton = QtGui.QPushButton("Collapse All")        
        collapseAllButton.clicked.connect(self.dewarTree.collapseAllCB)
        self.pauseQueueButton = QtGui.QPushButton("Pause")
        self.pauseQueueButton.clicked.connect(self.stopQueueCB) 
        emptyQueueButton = QtGui.QPushButton("Empty Queue")
        emptyQueueButton.clicked.connect(functools.partial(self.dewarTree.deleteSelectedCB,1))
        warmupButton = QtGui.QPushButton("Warmup Gripper")        
        warmupButton.clicked.connect(self.warmupGripperCB)
        restartServerButton = QtGui.QPushButton("Restart Server")        
        restartServerButton.clicked.connect(self.restartServerCB)
        self.openShutterButton = QtGui.QPushButton("Open Photon Shutter")        
        self.openShutterButton.clicked.connect(self.openPhotonShutterCB)
        self.popUserScreen = QtGui.QPushButton("User Screen...")
        self.popUserScreen.clicked.connect(self.popUserScreenCB)
        self.closeShutterButton = QtGui.QPushButton("Close Photon Shutter")        
        self.closeShutterButton.clicked.connect(self.closePhotonShutterCB)
        hBoxTreeButtsLayout = QtGui.QHBoxLayout()
        vBoxTreeButtsLayoutLeft = QtGui.QVBoxLayout()
        vBoxTreeButtsLayoutRight = QtGui.QVBoxLayout()
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
        vBoxTreeButtsLayoutRight.addWidget(restartServerButton)        
        hBoxTreeButtsLayout.addLayout(vBoxTreeButtsLayoutLeft)
        hBoxTreeButtsLayout.addLayout(vBoxTreeButtsLayoutRight)
        vBoxDFlayout.addLayout(hBoxTreeButtsLayout)
        self.dewarTreeFrame.setLayout(vBoxDFlayout)
        splitter1.addWidget(self.dewarTreeFrame)
        splitter11 = QtGui.QSplitter(Qt.Horizontal)
        self.mainSetupFrame = QFrame()
        self.mainSetupFrame.setFixedHeight(890)
        vBoxMainSetup = QtGui.QVBoxLayout()
        self.mainToolBox = QtGui.QToolBox()
        self.mainToolBox.setMinimumWidth(750)
        self.mainColFrame = QFrame()
        vBoxMainColLayout= QtGui.QVBoxLayout()
        colParamsGB = QtGui.QGroupBox()
        colParamsGB.setTitle("Acquisition")
        vBoxColParams1 = QtGui.QVBoxLayout()
        hBoxColParams1 = QtGui.QHBoxLayout()
        colStartLabel = QtGui.QLabel('Oscillation Start:')
        colStartLabel.setFixedWidth(140)
        colStartLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.osc_start_ledit = QtGui.QLineEdit()
        self.osc_start_ledit.setFixedWidth(60)
        self.colEndLabel = QtGui.QLabel('Oscillation Range:')
        self.colEndLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.colEndLabel.setFixedWidth(140)
        self.osc_end_ledit = QtGui.QLineEdit()
        self.osc_end_ledit.setText("180.0")
        self.osc_end_ledit.setFixedWidth(60)
        self.osc_end_ledit.textChanged[str].connect(functools.partial(self.totalExpChanged,"oscEnd"))        
        hBoxColParams1.addWidget(colStartLabel)
        hBoxColParams1.addWidget(self.osc_start_ledit)
        hBoxColParams1.addWidget(self.colEndLabel)
        hBoxColParams1.addWidget(self.osc_end_ledit)
        hBoxColParams2 = QtGui.QHBoxLayout()
        colRangeLabel = QtGui.QLabel('Oscillation Width:')
        colRangeLabel.setFixedWidth(140)
        colRangeLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.osc_range_ledit = QtGui.QLineEdit()
        self.osc_range_ledit.setFixedWidth(60)
        self.stillModeCheckBox = QCheckBox("Stills")
        self.stillModeCheckBox.setEnabled(False)
        if (self.stillModeStatePV.get()):
          self.stillModeCheckBox.setChecked(True)
          self.osc_range_ledit.setText("0.0")
        else:
          self.stillModeCheckBox.setChecked(False)          
        colExptimeLabel = QtGui.QLabel('ExposureTime:')
        self.stillModeCheckBox.clicked.connect(self.stillModeUserPushCB)        
        self.osc_range_ledit.textChanged[str].connect(functools.partial(self.totalExpChanged,"oscRange"))
        colExptimeLabel.setFixedWidth(140)
        colExptimeLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.exp_time_ledit = QtGui.QLineEdit()
        self.exp_time_ledit.setFixedWidth(60)
        self.exp_time_ledit.textChanged[str].connect(self.totalExpChanged)                
        hBoxColParams2.addWidget(colRangeLabel)
        hBoxColParams2.addWidget(self.osc_range_ledit)

        hBoxColParams2.addWidget(colExptimeLabel)
        hBoxColParams2.addWidget(self.exp_time_ledit)
        hBoxColParams25 = QtGui.QHBoxLayout()
        hBoxColParams25.addWidget(self.stillModeCheckBox)                
        totalExptimeLabel = QtGui.QLabel('Total Exposure Time (s):')
        totalExptimeLabel.setFixedWidth(155)
        totalExptimeLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.totalExptime_ledit = QtGui.QLabel()        
        self.totalExptime_ledit.setFixedWidth(60)
        sampleLifetimeLabel = QtGui.QLabel('Estimated Sample Lifetime (s): ')        
        if (daq_utils.beamline == "amx"):                                      
          self.sampleLifetimeReadback = QtEpicsPVLabel(daq_utils.pvLookupDict["sampleLifetime"],self,70,2)
          self.sampleLifetimeReadback_ledit = self.sampleLifetimeReadback.getEntry()
        else:
          calcLifetimeButton = QtGui.QPushButton("Calc. Lifetime")
          calcLifetimeButton.clicked.connect(self.calcLifetimeCB)
          self.sampleLifetimeReadback_ledit = QtGui.QLabel()
          self.calcLifetimeCB()
        hBoxColParams25.addWidget(totalExptimeLabel)
        hBoxColParams25.addWidget(self.totalExptime_ledit)
        if (daq_utils.beamline == "fmx"):
          hBoxColParams25.addWidget(calcLifetimeButton)
        hBoxColParams25.addWidget(sampleLifetimeLabel)
        hBoxColParams25.addWidget(self.sampleLifetimeReadback_ledit)
        hBoxColParams22 = QtGui.QHBoxLayout()
        if (daq_utils.beamline == "fmx"):
          if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"attenType") == "RI"):
            self.transmissionReadback = QtEpicsPVLabel(daq_utils.pvLookupDict["RI_Atten_SP"],self,60,3)
            self.transmissionSetPoint = QtEpicsPVEntry(daq_utils.pvLookupDict["RI_Atten_SP"],self,60,3)
            colTransmissionLabel = QtGui.QLabel('Transmission (RI) (0.0-1.0):')            
          else:
            self.transmissionReadback = QtEpicsPVLabel(daq_utils.pvLookupDict["transmissionRBV"],self,60,3)
            self.transmissionSetPoint = QtEpicsPVEntry(daq_utils.pvLookupDict["transmissionSet"],self,60,3)
            colTransmissionLabel = QtGui.QLabel('Transmission (BCU) (0.0-1.0):')            
        else:
            self.transmissionReadback = QtEpicsPVLabel(daq_utils.pvLookupDict["transmissionRBV"],self,60,3)
            self.transmissionSetPoint = QtEpicsPVEntry(daq_utils.pvLookupDict["transmissionSet"],self,60,3)
            colTransmissionLabel = QtGui.QLabel('Transmission (0.0-1.0):')            
        self.transmissionReadback_ledit = self.transmissionReadback.getEntry()

        colTransmissionLabel.setAlignment(QtCore.Qt.AlignCenter) 
        colTransmissionLabel.setFixedWidth(190)
        
        transmisionSPLabel = QtGui.QLabel("SetPoint:")

        self.transmission_ledit = self.transmissionSetPoint.getEntry()
        self.transmission_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"stdTrans")))
        self.transmission_ledit.returnPressed.connect(self.setTransCB)        
        setTransButton = QtGui.QPushButton("Set Trans")
        setTransButton.clicked.connect(self.setTransCB)
        beamsizeLabel = QtGui.QLabel("BeamSize:")        
        beamSizeOptionList = ["V0H0","V0H1","V1H0","V1H1"]
        self.beamsizeComboBox = QtGui.QComboBox(self)
        self.beamsizeComboBox.addItems(beamSizeOptionList)
        self.beamsizeComboBox.setCurrentIndex(int(self.beamSize_pv.get()))
        self.beamsizeComboBox.activated[str].connect(self.beamsizeComboActivatedCB)
        if (daq_utils.beamline == "amx" or self.energy_pv.get() < 9000):
          self.beamsizeComboBox.setEnabled(False)
        hBoxColParams3 = QtGui.QHBoxLayout()
        colEnergyLabel = QtGui.QLabel('Energy (eV):')
        colEnergyLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.energyMotorEntry = QtEpicsPVLabel(daq_utils.motor_dict["energy"]+ ".RBV",self,70,2)
        self.energyReadback = self.energyMotorEntry.getEntry()
        energySPLabel = QtGui.QLabel("SetPoint:")
        self.energyMoveLedit = QtEpicsPVEntry(daq_utils.motor_dict["energy"] + ".VAL",self,75,2)
        self.energy_ledit = self.energyMoveLedit.getEntry()
        self.energy_ledit.returnPressed.connect(self.moveEnergyCB)        
        moveEnergyButton = QtGui.QPushButton("Move Energy")
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
        hBoxColParams4 = QtGui.QHBoxLayout()
        colBeamWLabel = QtGui.QLabel('Beam Width:')
        colBeamWLabel.setFixedWidth(140)
        colBeamWLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.beamWidth_ledit = QtGui.QLineEdit()
        self.beamWidth_ledit.setFixedWidth(60)
        colBeamHLabel = QtGui.QLabel('Beam Height:')
        colBeamHLabel.setFixedWidth(140)
        colBeamHLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.beamHeight_ledit = QtGui.QLineEdit()
        self.beamHeight_ledit.setFixedWidth(60)
        hBoxColParams4.addWidget(colBeamWLabel)
        hBoxColParams4.addWidget(self.beamWidth_ledit)
        hBoxColParams4.addWidget(colBeamHLabel)
        hBoxColParams4.addWidget(self.beamHeight_ledit)
        hBoxColParams5 = QtGui.QHBoxLayout()
        colResoLabel = QtGui.QLabel('Edge Resolution:')
        colResoLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.resolution_ledit = QtGui.QLineEdit()
        self.resolution_ledit.setFixedWidth(60)
        self.resolution_ledit.textEdited[str].connect(self.resoTextChanged)
        detDistLabel = QtGui.QLabel('Detector Dist.')
        detDistLabel.setAlignment(QtCore.Qt.AlignCenter)         
        detDistRBLabel = QtGui.QLabel("Readback:")
        self.detDistRBVLabel = QtEpicsPVLabel(daq_utils.motor_dict["detectorDist"] + ".RBV",self,70) 
        detDistSPLabel = QtGui.QLabel("SetPoint:")
        self.detDistMotorEntry = QtEpicsPVEntry(daq_utils.motor_dict["detectorDist"] + ".VAL",self,70,2)
        self.detDistMotorEntry.getEntry().textChanged[str].connect(self.detDistTextChanged)
        self.detDistMotorEntry.getEntry().returnPressed.connect(self.moveDetDistCB)        
        self.moveDetDistButton = QtGui.QPushButton("Move Detector")
        self.moveDetDistButton.clicked.connect(self.moveDetDistCB)
        hBoxColParams3.addWidget(detDistLabel)
        hBoxColParams3.addWidget(self.detDistRBVLabel.getEntry())
        hBoxColParams3.addWidget(detDistSPLabel)        
        hBoxColParams3.addWidget(self.detDistMotorEntry.getEntry())
        hBoxColParams6 = QtGui.QHBoxLayout()
        hBoxColParams6.setAlignment(QtCore.Qt.AlignLeft) 
        hBoxColParams7 = QtGui.QHBoxLayout()
        hBoxColParams7.setAlignment(QtCore.Qt.AlignLeft) 
        centeringLabel = QtGui.QLabel('Sample Centering:')
        centeringLabel.setFixedWidth(140)        
        centeringOptionList = ["Interactive","AutoLoop","AutoRaster","Testing"]
        self.centeringComboBox = QtGui.QComboBox(self)
        self.centeringComboBox.addItems(centeringOptionList)
        protoLabel = QtGui.QLabel('Protocol:')
        font = QtGui.QFont()
        font.setBold(True)
        protoLabel.setFont(font)
        protoLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.protoRadioGroup=QtGui.QButtonGroup()
        self.protoStandardRadio = QtGui.QRadioButton("standard")
        self.protoStandardRadio.setChecked(True)
        self.protoStandardRadio.toggled.connect(functools.partial(self.protoRadioToggledCB,"standard"))
        self.protoStandardRadio.pressed.connect(functools.partial(self.protoRadioToggledCB,"standard"))        
        self.protoRadioGroup.addButton(self.protoStandardRadio)
        self.protoRasterRadio = QtGui.QRadioButton("raster")
        self.protoRasterRadio.toggled.connect(functools.partial(self.protoRadioToggledCB,"raster"))
        self.protoRasterRadio.pressed.connect(functools.partial(self.protoRadioToggledCB,"raster"))                
        self.protoRadioGroup.addButton(self.protoRasterRadio)
        self.protoVectorRadio = QtGui.QRadioButton("vector")
        self.protoRasterRadio.toggled.connect(functools.partial(self.protoRadioToggledCB,"vector"))
        self.protoRasterRadio.pressed.connect(functools.partial(self.protoRadioToggledCB,"vector"))        
        self.protoRadioGroup.addButton(self.protoVectorRadio)
        self.protoOtherRadio = QtGui.QRadioButton("other")
        self.protoOtherRadio.setEnabled(False)
        self.protoRadioGroup.addButton(self.protoOtherRadio)
        protoOptionList = ["standard","screen","raster","vector","burn","eScan","rasterScreen","stepRaster","stepVector","multiCol","characterize","ednaCol","specRaster"] # these should probably come from db
        self.protoComboBox = QtGui.QComboBox(self)
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
        self.hBoxProcessingLayout1= QtGui.QHBoxLayout()        
        self.hBoxProcessingLayout1.setAlignment(QtCore.Qt.AlignLeft) 
        procOptionLabel = QtGui.QLabel('Processing Options:')
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
        self.dimpleCheckBox.setChecked(False)        
        self.xia2CheckBox = QCheckBox("Xia2")
        self.xia2CheckBox.setChecked(False)
        self.hBoxProcessingLayout1.addWidget(self.autoProcessingCheckBox)                
        self.hBoxProcessingLayout1.addWidget(self.fastDPCheckBox)
        self.hBoxProcessingLayout1.addWidget(self.fastEPCheckBox)
        self.hBoxProcessingLayout1.addWidget(self.dimpleCheckBox)                
        self.processingOptionsFrame.setLayout(self.hBoxProcessingLayout1)
        self.rasterParamsFrame = QFrame()
        self.vBoxRasterParams = QtGui.QVBoxLayout()
        self.hBoxRasterLayout1= QtGui.QHBoxLayout()        
        self.hBoxRasterLayout1.setAlignment(QtCore.Qt.AlignLeft) 
        self.hBoxRasterLayout2= QtGui.QHBoxLayout()        
        self.hBoxRasterLayout2.setAlignment(QtCore.Qt.AlignLeft) 
        rasterStepLabel = QtGui.QLabel('Raster Step')
        rasterStepLabel.setFixedWidth(110)
        self.rasterStepEdit = QtGui.QLineEdit(str(self.rasterStepDefs["Coarse"]))
        self.rasterStepEdit.textChanged[str].connect(self.rasterStepChanged)        
        self.rasterStepEdit.setFixedWidth(60)
        self.rasterGrainRadioGroup=QtGui.QButtonGroup()
        self.rasterGrainCoarseRadio = QtGui.QRadioButton("Coarse")
        self.rasterGrainCoarseRadio.setChecked(False)
        self.rasterGrainCoarseRadio.toggled.connect(functools.partial(self.rasterGrainToggledCB,"Coarse"))
        self.rasterGrainRadioGroup.addButton(self.rasterGrainCoarseRadio)
        self.rasterGrainFineRadio = QtGui.QRadioButton("Fine")
        self.rasterGrainFineRadio.setChecked(False)
        self.rasterGrainFineRadio.toggled.connect(functools.partial(self.rasterGrainToggledCB,"Fine"))
        self.rasterGrainRadioGroup.addButton(self.rasterGrainFineRadio)
        self.rasterGrainVFineRadio = QtGui.QRadioButton("VFine")
        self.rasterGrainVFineRadio.setChecked(False)
        self.rasterGrainVFineRadio.toggled.connect(functools.partial(self.rasterGrainToggledCB,"VFine"))
        self.rasterGrainRadioGroup.addButton(self.rasterGrainVFineRadio)
        self.rasterGrainCustomRadio = QtGui.QRadioButton("Custom")
        self.rasterGrainCustomRadio.setChecked(True)
        self.rasterGrainCustomRadio.toggled.connect(functools.partial(self.rasterGrainToggledCB,"Custom"))
        self.rasterGrainRadioGroup.addButton(self.rasterGrainCustomRadio)
        rasterEvalLabel = QtGui.QLabel('Raster\nEvaluate By:')
        rasterEvalOptionList = ["Spot Count","Resolution","Intensity"]
        self.rasterEvalComboBox = QtGui.QComboBox(self)
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
        self.hBoxMultiColParamsLayout1 = QtGui.QHBoxLayout()
        self.hBoxMultiColParamsLayout1.setAlignment(QtCore.Qt.AlignLeft)
        multiColCutoffLabel = QtGui.QLabel('Diffraction Cutoff')
        multiColCutoffLabel.setFixedWidth(110)
        self.multiColCutoffEdit = QtGui.QLineEdit("320") #may need to store this in DB at some point, it's a silly number for now
        self.multiColCutoffEdit.setFixedWidth(60)
        self.hBoxMultiColParamsLayout1.addWidget(multiColCutoffLabel)
        self.hBoxMultiColParamsLayout1.addWidget(self.multiColCutoffEdit)
        self.multiColParamsFrame.setLayout(self.hBoxMultiColParamsLayout1)
        self.characterizeParamsFrame = QFrame()
        vBoxCharacterizeParams1 = QtGui.QVBoxLayout()
        self.hBoxCharacterizeLayout1= QtGui.QHBoxLayout() 
        self.characterizeTargetLabel = QtGui.QLabel('Characterization Targets')       
        characterizeResoLabel = QtGui.QLabel('Resolution')
        characterizeResoLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeResoEdit = QtGui.QLineEdit("3.0")
        characterizeISIGLabel = QtGui.QLabel('I/Sigma')
        characterizeISIGLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeISIGEdit = QtGui.QLineEdit("2.0")
        self.characterizeAnomCheckBox = QCheckBox("Anomolous")
        self.characterizeAnomCheckBox.setChecked(False)
        self.hBoxCharacterizeLayout2 = QtGui.QHBoxLayout() 
        characterizeCompletenessLabel = QtGui.QLabel('Completeness')
        characterizeCompletenessLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeCompletenessEdit = QtGui.QLineEdit("0.99")
        characterizeMultiplicityLabel = QtGui.QLabel('Multiplicity')
        characterizeMultiplicityLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeMultiplicityEdit = QtGui.QLineEdit("auto")
        characterizeDoseLimitLabel = QtGui.QLabel('Dose Limit')
        characterizeDoseLimitLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeDoseLimitEdit = QtGui.QLineEdit("100")
        characterizeSpaceGroupLabel = QtGui.QLabel('Space Group')
        characterizeSpaceGroupLabel.setAlignment(QtCore.Qt.AlignCenter) 
        self.characterizeSpaceGroupEdit = QtGui.QLineEdit("P1")
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
        hBoxVectorLayout1= QtGui.QHBoxLayout() 
        setVectorStartButton = QtGui.QPushButton("Vector\nStart") 
        setVectorStartButton.clicked.connect(self.setVectorStartCB)
        setVectorEndButton = QtGui.QPushButton("Vector\nEnd") 
        setVectorEndButton.clicked.connect(self.setVectorEndCB)
        vectorFPPLabel = QtGui.QLabel("Number of Wedges")
        self.vectorFPP_ledit = QtGui.QLineEdit("1")
        vecLenLabel = QtGui.QLabel("    Length(microns):")
        self.vecLenLabelOutput = QtGui.QLabel("---")
        vecSpeedLabel = QtGui.QLabel("    Speed(microns/s):")
        self.vecSpeedLabelOutput = QtGui.QLabel("---")
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
        hBoxDisplayOptionLayout= QtGui.QHBoxLayout()        
        self.albulaDispCheckBox = QCheckBox("Display Data (Albula)")
        self.albulaDispCheckBox.setChecked(False)
        hBoxDisplayOptionLayout.addWidget(self.albulaDispCheckBox)
        vBoxMainColLayout.addWidget(colParamsGB)
        vBoxMainColLayout.addWidget(self.dataPathGB)
        vBoxMainColLayout.addLayout(hBoxDisplayOptionLayout)
        self.mainColFrame.setLayout(vBoxMainColLayout)
        self.EScanToolFrame = QFrame()
        vBoxEScanTool = QtGui.QVBoxLayout()
        self.periodicTableTool = QPeriodicTable(butSize=20)
        self.EScanDataPathGBTool = DataLocInfo(self)
        vBoxEScanTool.addWidget(self.periodicTableTool)
        vBoxEScanTool.addWidget(self.EScanDataPathGBTool)
        self.EScanToolFrame.setLayout(vBoxEScanTool)
        self.mainToolBox.addItem(self.mainColFrame,"Collection Parameters")        
        editSampleButton = QtGui.QPushButton("Apply Changes") 
        editSampleButton.clicked.connect(self.editSelectedRequestsCB)
        cloneRequestButton = QtGui.QPushButton("Clone Raster Request") 
        cloneRequestButton.clicked.connect(self.cloneRequestCB)
        hBoxPriorityLayout1= QtGui.QHBoxLayout()        
        priorityEditLabel = QtGui.QLabel("Priority Edit")
        priorityTopButton =  QtGui.QPushButton("   >>   ")
        priorityUpButton =   QtGui.QPushButton("   >    ")
        priorityDownButton = QtGui.QPushButton("   <    ")
        priorityBottomButton=QtGui.QPushButton("   <<   ")
        priorityTopButton.clicked.connect(self.topPriorityCB)
        priorityBottomButton.clicked.connect(self.bottomPriorityCB)
        priorityUpButton.clicked.connect(self.upPriorityCB)
        priorityDownButton.clicked.connect(self.downPriorityCB)
        hBoxPriorityLayout1.addWidget(priorityEditLabel)
        hBoxPriorityLayout1.addWidget(priorityBottomButton)
        hBoxPriorityLayout1.addWidget(priorityDownButton)
        hBoxPriorityLayout1.addWidget(priorityUpButton)
        hBoxPriorityLayout1.addWidget(priorityTopButton)
        queueSampleButton = QtGui.QPushButton("Add Requests to Queue") 
        queueSampleButton.clicked.connect(self.addRequestsToAllSelectedCB)
        deleteSampleButton = QtGui.QPushButton("Delete Requests") 
        deleteSampleButton.clicked.connect(functools.partial(self.dewarTree.deleteSelectedCB,0))
        editScreenParamsButton = QtGui.QPushButton("Edit Raster Params...") 
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
        vBoxVidLayout= QtGui.QVBoxLayout()
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
        time.sleep(5) # is this needed????
        self.capture = self.captureLowMag
        self.timerHutch = QTimer()
        self.timerHutch.timeout.connect(self.timerHutchRefresh)
        self.timerHutch.start(500)

        self.timerSample = QTimer()
        self.timerSample.timeout.connect(self.timerSampleRefresh)
        self.timerSample.start(0)
        self.centeringMarksList = []
        self.rasterList = []
        self.rasterDefList = []
        self.polyPointItems = []
        self.rasterPoly = None
        self.measureLine = None
        self.scene = QtGui.QGraphicsScene(0,0,640,512,self)
        hBoxHutchVidsLayout= QtGui.QHBoxLayout()
        self.sceneHutchCorner = QtGui.QGraphicsScene(0,0,320,180,self)
        self.sceneHutchTop = QtGui.QGraphicsScene(0,0,320,180,self)                        
        self.scene.keyPressEvent = self.sceneKey
        self.view = QtGui.QGraphicsView(self.scene)
        self.viewHutchCorner = QtGui.QGraphicsView(self.sceneHutchCorner)
        self.viewHutchTop = QtGui.QGraphicsView(self.sceneHutchTop)                
        self.pixmap_item = QtGui.QGraphicsPixmapItem(None, self.scene)
        self.pixmap_item_HutchCorner = QtGui.QGraphicsPixmapItem(None, self.sceneHutchCorner)
        self.pixmap_item_HutchTop = QtGui.QGraphicsPixmapItem(None, self.sceneHutchTop)                      
        self.pixmap_item.mousePressEvent = self.pixelSelect
        centerMarkBrush = QtGui.QBrush(QtCore.Qt.blue)                
        centerMarkPen = QtGui.QPen(centerMarkBrush,2.0)
        self.centerMarker = QtGui.QGraphicsSimpleTextItem("+")
        self.centerMarker.setZValue(10.0)
        self.centerMarker.setBrush(centerMarkBrush)
        font = QtGui.QFont('DejaVu Sans Light', self.centerMarkerCharSize,weight=0)
        self.centerMarker.setFont(font)        
        self.scene.addItem(self.centerMarker)
        self.centerMarker.setPos(daq_utils.screenPixCenterX-self.centerMarkerCharOffsetX,daq_utils.screenPixCenterY-self.centerMarkerCharOffsetY)
        self.zoomRadioGroup=QtGui.QButtonGroup()
        self.zoom1Radio = QtGui.QRadioButton("Mag1")
        self.zoom1Radio.setChecked(True)
        self.zoom1Radio.toggled.connect(functools.partial(self.zoomLevelToggledCB,"Zoom1"))
        self.zoomRadioGroup.addButton(self.zoom1Radio)
        self.zoom2Radio = QtGui.QRadioButton("Mag2")
        self.zoom2Radio.toggled.connect(functools.partial(self.zoomLevelToggledCB,"Zoom2"))
        self.zoomRadioGroup.addButton(self.zoom2Radio)
        self.zoom3Radio = QtGui.QRadioButton("Mag3")
        self.zoom3Radio.toggled.connect(functools.partial(self.zoomLevelToggledCB,"Zoom3"))
        self.zoomRadioGroup.addButton(self.zoom3Radio)
        self.zoom4Radio = QtGui.QRadioButton("Mag4")
        self.zoom4Radio.toggled.connect(functools.partial(self.zoomLevelToggledCB,"Zoom4"))
        self.zoomRadioGroup.addButton(self.zoom4Radio)
        beamOverlayPen = QtGui.QPen(QtCore.Qt.red)
        self.tempBeamSizeXMicrons = 30
        self.tempBeamSizeYMicrons = 30        
        self.beamSizeXPixels = self.screenXmicrons2pixels(self.tempBeamSizeXMicrons)
        self.beamSizeYPixels = self.screenYmicrons2pixels(self.tempBeamSizeYMicrons)
        self.overlayPosOffsetX = self.centerMarkerCharOffsetX-1
        self.overlayPosOffsetY = self.centerMarkerCharOffsetY-1     
        self.beamSizeOverlay = QtGui.QGraphicsRectItem(self.centerMarker.x()-self.overlayPosOffsetX,self.centerMarker.y()-self.overlayPosOffsetY,self.beamSizeXPixels,self.beamSizeYPixels)
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
        hBoxSampleOrientationLayout = QtGui.QHBoxLayout()
        setDC2CPButton = QtGui.QPushButton("SetStart")
        setDC2CPButton.clicked.connect(self.setDCStartCB)        
        omegaLabel = QtGui.QLabel("Omega:")
        omegaMonitorPV = str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"omegaMonitorPV"))
        self.sampleOmegaRBVLedit = QtEpicsPVLabel(daq_utils.motor_dict["omega"] + "." + omegaMonitorPV,self,70) 
        omegaSPLabel = QtGui.QLabel("SetPoint:")
        self.sampleOmegaMoveLedit = QtEpicsPVEntry(daq_utils.motor_dict["omega"] + ".VAL",self,70,2)
        self.sampleOmegaMoveLedit.getEntry().returnPressed.connect(self.moveOmegaCB)
        moveOmegaButton = QtGui.QPushButton("Move")
        moveOmegaButton.clicked.connect(self.moveOmegaCB)
        omegaTweakNegButtonFine = QtGui.QPushButton("-5")        
        omegaTweakNegButton = QtGui.QPushButton("<")
        omegaTweakNegButton.clicked.connect(self.omegaTweakNegCB)
        omegaTweakNegButtonFine.clicked.connect(functools.partial(self.omegaTweakCB,-5))
        self.omegaTweakVal_ledit = QtGui.QLineEdit()
        self.omegaTweakVal_ledit.setFixedWidth(60)
        self.omegaTweakVal_ledit.setText("90")
        omegaTweakPosButtonFine = QtGui.QPushButton("+5")        
        omegaTweakPosButton = QtGui.QPushButton(">")
        omegaTweakPosButton.clicked.connect(self.omegaTweakPosCB)
        omegaTweakPosButtonFine.clicked.connect(functools.partial(self.omegaTweakCB,5))
        hBoxSampleOrientationLayout.addWidget(setDC2CPButton)
        hBoxSampleOrientationLayout.addWidget(omegaLabel)
        hBoxSampleOrientationLayout.addWidget(self.sampleOmegaRBVLedit.getEntry())
        hBoxSampleOrientationLayout.addWidget(omegaSPLabel)
        hBoxSampleOrientationLayout.addWidget(self.sampleOmegaMoveLedit.getEntry())
        spacerItem = QtGui.QSpacerItem(100, 1, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        hBoxSampleOrientationLayout.insertSpacing(6,100)
        hBoxSampleOrientationLayout.addWidget(omegaTweakNegButtonFine)
        hBoxSampleOrientationLayout.addWidget(omegaTweakNegButton)        
        hBoxSampleOrientationLayout.addWidget(self.omegaTweakVal_ledit)
        hBoxSampleOrientationLayout.addWidget(omegaTweakPosButton)
        hBoxSampleOrientationLayout.addWidget(omegaTweakPosButtonFine)        
        hBoxSampleOrientationLayout.addStretch(1)
        hBoxVidControlLayout = QtGui.QHBoxLayout()
        lightLevelLabel = QtGui.QLabel("Light")
        lightLevelLabel.setAlignment(QtCore.Qt.AlignRight|Qt.AlignVCenter)         
        sampleBrighterButton = QtGui.QPushButton("+")
        sampleBrighterButton.setFixedWidth(30)
        sampleBrighterButton.clicked.connect(self.lightUpCB)
        sampleDimmerButton = QtGui.QPushButton("-")
        sampleDimmerButton.setFixedWidth(30)
        sampleDimmerButton.clicked.connect(self.lightDimCB)
        focusLabel = QtGui.QLabel("Focus")
        focusLabel.setAlignment(QtCore.Qt.AlignRight|Qt.AlignVCenter)         
        focusPlusButton = QtGui.QPushButton("+")
        focusPlusButton.setFixedWidth(30)
        focusPlusButton.clicked.connect(functools.partial(self.focusTweakCB,5))        
        focusMinusButton = QtGui.QPushButton("-")
        focusMinusButton.setFixedWidth(30)
        focusMinusButton.clicked.connect(functools.partial(self.focusTweakCB,-5))
        annealButton = QtGui.QPushButton("Anneal")
        annealButton.clicked.connect(self.annealButtonCB)
        if (daq_utils.beamline == "fmx"):
          annealButton.setEnabled(False)
        annealTimeLabel = QtGui.QLabel("Time")
        self.annealTime_ledit = QtGui.QLineEdit()
        self.annealTime_ledit.setFixedWidth(40)
        self.annealTime_ledit.setText("0.5")
        magLevelLabel = QtGui.QLabel("Vid:")
        snapshotButton = QtGui.QPushButton("SnapShot")        
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
        hBoxSampleAlignLayout = QtGui.QHBoxLayout()
        centerLoopButton = QtGui.QPushButton("Center\nLoop")
        centerLoopButton.clicked.connect(self.autoCenterLoopCB)
        measureButton = QtGui.QPushButton("Measure")
        measureButton.clicked.connect(self.measurePolyCB)
        loopShapeButton = QtGui.QPushButton("Add Raster\nto Queue")
        loopShapeButton.clicked.connect(self.drawInteractiveRasterCB)
        runRastersButton = QtGui.QPushButton("Run\nRaster")
        runRastersButton.clicked.connect(self.runRastersCB)
        clearGraphicsButton = QtGui.QPushButton("Clear")
        clearGraphicsButton.clicked.connect(self.eraseCB)
        self.click3Button = QtGui.QPushButton("3-Click\nCenter")
        self.click3Button.clicked.connect(self.center3LoopCB)
        self.threeClickCount = 0
        saveCenteringButton = QtGui.QPushButton("Save\nCenter")
        saveCenteringButton.clicked.connect(self.saveCenterCB)
        selectAllCenteringButton = QtGui.QPushButton("Select All\nCenterings")
        selectAllCenteringButton.clicked.connect(self.selectAllCenterCB)
        hBoxSampleAlignLayout.addWidget(centerLoopButton)
        hBoxSampleAlignLayout.addWidget(clearGraphicsButton)
        hBoxSampleAlignLayout.addWidget(saveCenteringButton)
        hBoxSampleAlignLayout.addWidget(selectAllCenteringButton)
        hBoxSampleAlignLayout.addWidget(self.click3Button)
        hBoxSampleAlignLayout.addWidget(snapshotButton)
        hBoxSampleAlignLayout.addWidget(self.hideRastersCheckBox)                        
        hBoxRadioLayout100= QtGui.QHBoxLayout()
        vidActionLabel = QtGui.QLabel("Video Click Mode:")        
        self.vidActionRadioGroup=QtGui.QButtonGroup()
        self.vidActionC2CRadio = QtGui.QRadioButton("C2C")
        self.vidActionC2CRadio.setChecked(True)
        self.vidActionC2CRadio.toggled.connect(self.vidActionToggledCB)
        self.vidActionRadioGroup.addButton(self.vidActionC2CRadio)        
        self.vidActionDefineCenterRadio = QtGui.QRadioButton("Define Center")
        self.vidActionDefineCenterRadio.setChecked(False)
        self.vidActionDefineCenterRadio.setEnabled(False)        
        self.vidActionDefineCenterRadio.toggled.connect(self.vidActionToggledCB)
        self.vidActionRadioGroup.addButton(self.vidActionDefineCenterRadio)
        self.vidActionRasterExploreRadio = QtGui.QRadioButton("Raster Explore")
        self.vidActionRasterExploreRadio.setChecked(False)
        self.vidActionRasterExploreRadio.toggled.connect(self.vidActionToggledCB)
        self.vidActionRadioGroup.addButton(self.vidActionRasterExploreRadio)
        self.vidActionRasterSelectRadio = QtGui.QRadioButton("Raster Select")
        self.vidActionRasterSelectRadio.setChecked(False)
        self.vidActionRasterSelectRadio.toggled.connect(self.vidActionToggledCB)
        self.vidActionRasterDefRadio = QtGui.QRadioButton("Define Raster")
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
        self.colTabs= QtGui.QTabWidget()        
        self.energyFrame = QFrame()
        vBoxEScanFull = QtGui.QVBoxLayout()
        hBoxEScan = QtGui.QHBoxLayout()
        vBoxEScan = QtGui.QVBoxLayout()
        self.periodicTable = QPeriodicTable(butSize=20)
        self.periodicTable.elementClicked("Se")
        vBoxEScan.addWidget(self.periodicTable)
        self.EScanDataPathGB = DataLocInfo(self)
        vBoxEScan.addWidget(self.EScanDataPathGB)
        hBoxEScanParams = QtGui.QHBoxLayout()
        hBoxEScanButtons = QtGui.QHBoxLayout()                        
        tempPlotButton = QtGui.QPushButton("Queue Requests")        
        tempPlotButton.clicked.connect(self.queueEnScanCB)
        clearEnscanPlotButton = QtGui.QPushButton("Clear")        
        clearEnscanPlotButton.clicked.connect(self.clearEnScanPlotCB)        
        hBoxEScanButtons.addWidget(clearEnscanPlotButton)
        hBoxEScanButtons.addWidget(tempPlotButton)
        escanStepsLabel = QtGui.QLabel("Steps")        
        self.escan_steps_ledit = QtGui.QLineEdit()
        self.escan_steps_ledit.setText("41")
        escanStepsizeLabel = QtGui.QLabel("Stepsize (EVs)")        
        self.escan_stepsize_ledit = QtGui.QLineEdit()
        self.escan_stepsize_ledit.setText("1")
        hBoxEScanParams.addWidget(escanStepsLabel)
        hBoxEScanParams.addWidget(self.escan_steps_ledit)
        hBoxEScanParams.addWidget(escanStepsizeLabel)
        hBoxEScanParams.addWidget(self.escan_stepsize_ledit)
        hBoxChoochResults = QtGui.QHBoxLayout()
        hBoxChoochResults2 = QtGui.QHBoxLayout()        
        choochResultsLabel = QtGui.QLabel("Chooch Results")
        choochInflLabel = QtGui.QLabel("Infl")
        self.choochInfl = QtGui.QLabel("")
        self.choochInfl.setFixedWidth(70)                
        choochPeakLabel = QtGui.QLabel("Peak")
        self.choochPeak = QtGui.QLabel("")
        self.choochPeak.setFixedWidth(70)
        choochInflFPrimeLabel = QtGui.QLabel("fPrimeInfl")
        self.choochFPrimeInfl = QtGui.QLabel("")
        self.choochFPrimeInfl.setFixedWidth(70)                
        choochInflF2PrimeLabel = QtGui.QLabel("f2PrimeInfl")
        self.choochF2PrimeInfl = QtGui.QLabel("")
        self.choochF2PrimeInfl.setFixedWidth(70)                
        choochPeakFPrimeLabel = QtGui.QLabel("fPrimePeak")
        self.choochFPrimePeak = QtGui.QLabel("")
        self.choochFPrimePeak.setFixedWidth(70)                
        choochPeakF2PrimeLabel = QtGui.QLabel("f2PrimePeak")
        self.choochF2PrimePeak = QtGui.QLabel("")
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
        self.EScanGraph = QtBlissGraph(self.energyFrame)
        hBoxEScan.addWidget(verticalLine)
        hBoxEScan.addWidget(self.EScanGraph)
        vBoxEScanFull.addLayout(hBoxEScan)
        self.choochGraph = QtBlissGraph(self.energyFrame)
        vBoxEScanFull.addWidget(self.choochGraph)
        self.energyFrame.setLayout(vBoxEScanFull)
        splitter11.addWidget(self.VidFrame)
        self.colTabs.addTab(splitter11,"Sample Control")
        self.colTabs.addTab(self.energyFrame,"Energy Scan")
        splitter1.addWidget(self.colTabs)
        vBoxlayout.addWidget(splitter1)
        self.lastFileLabel2 = QtGui.QLabel('File:')
        self.lastFileLabel2.setFixedWidth(60)
        if (daq_utils.beamline == "amx"):                    
          self.lastFileRBV2 = QtEpicsPVLabel("XF:17IDB-ES:AMX{Det:Eig9M}cam1:FullFileName_RBV",self,0)            
        else:
          self.lastFileRBV2 = QtEpicsPVLabel("XF:17IDC-ES:FMX{Det:Eig16M}cam1:FullFileName_RBV",self,0)            
        fileHBoxLayout = QtGui.QHBoxLayout()
        fileHBoxLayout2 = QtGui.QHBoxLayout()        
        self.controlMasterCheckBox = QCheckBox("Control Master")
        self.controlMasterCheckBox.stateChanged.connect(self.changeControlMasterCB)
        self.controlMasterCheckBox.setChecked(False)
        fileHBoxLayout.addWidget(self.controlMasterCheckBox)        
        self.statusLabel = QtEpicsPVLabel(daq_utils.beamlineComm+"program_state",self,150,highlight_on_change=False)
        fileHBoxLayout.addWidget(self.statusLabel.getEntry())
        self.shutterStateLabel = QtGui.QLabel('Shutter State:')
        governorMessageLabel = QtGui.QLabel('Governor Message:')
        self.governorMessage = QtEpicsPVLabel(daq_utils.pvLookupDict["governorMessage"],self,140,highlight_on_change=False)
        ringCurrentMessageLabel = QtGui.QLabel('Ring(mA):')
        self.ringCurrentMessage = QtGui.QLabel(str(self.ringCurrent_pv.get()))
        beamAvailable = self.beamAvailable_pv.get()
        if (beamAvailable):
          self.beamAvailLabel = QtGui.QLabel("Beam Available")
          self.beamAvailLabel.setStyleSheet("background-color: #99FF66;")                  
        else:
          self.beamAvailLabel = QtGui.QLabel("No Beam")
          self.beamAvailLabel.setStyleSheet("background-color: red;")                  
        sampleExposed = self.sampleExposed_pv.get()
        if (sampleExposed):
          self.sampleExposedLabel = QtGui.QLabel("Sample Exposed")
          self.sampleExposedLabel.setStyleSheet("background-color: red;")                  
        else:
          self.sampleExposedLabel = QtGui.QLabel("Sample Not Exposed")
          self.sampleExposedLabel.setStyleSheet("background-color: #99FF66;")              
        gripperLabel = QtGui.QLabel('Gripper Temp:')
        self.gripperTempLabel = QtGui.QLabel(str(self.gripTemp_pv.get()))
        fileHBoxLayout.addWidget(gripperLabel)
        fileHBoxLayout.addWidget(self.gripperTempLabel)
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
        self.XRFTab = QtGui.QFrame()        
        XRFhBox = QtGui.QHBoxLayout()
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
          self.osc_range_ledit.setText("0.0")
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
              self.rasterList[i]["graphicsItem"].setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)            
        else:
          for i in range(len(self.rasterList)):
            if (self.rasterList[i] != None):
              self.rasterList[i]["graphicsItem"].setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)
              self.rasterList[i]["graphicsItem"].setFlag(QtGui.QGraphicsItem.ItemIsSelectable, False)
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
              self.fillPolyRaster(db_lib.getRequestByID(saveRasterList[i]["uid"]),takeSnapshot=False)
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
        if (float(self.osc_range_ledit.text()) == 0):
          self.stillMode_pv.put(1)
        else:
          self.standardMode_pv.put(1)                      
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
          if (self.vectorEnd != None):
            startYX = self.vectorEnd["coords"]["y"]
            startYY = self.vectorEnd["coords"]["z"]
            newY = self.calculateNewYCoordPos(startYX,startYY)
            self.vectorEnd["graphicsitem"].setPos(self.vectorEnd["graphicsitem"].x(),newY-centerMarkerOffsetY)
        if (motID == "x"):
          startX = self.vectorStart["coords"]["x"]
          delta = startX-posRBV
          newX = float(self.screenXmicrons2pixels(delta))
          self.vectorStart["graphicsitem"].setPos(newX-centerMarkerOffsetX,self.vectorStart["graphicsitem"].y())
          if (self.vectorEnd != None):
            startX = self.vectorEnd["coords"]["x"]
            delta = startX-posRBV
            newX = float(self.screenXmicrons2pixels(delta))
            self.vectorEnd["graphicsitem"].setPos(newX-centerMarkerOffsetX,self.vectorEnd["graphicsitem"].y())
        if (motID == "y" or motID == "z"):
          startYX = self.vectorStart["coords"]["y"]
          startYY = self.vectorStart["coords"]["z"]
          newY = self.calculateNewYCoordPos(startYX,startYY)
          self.vectorStart["graphicsitem"].setPos(self.vectorStart["graphicsitem"].x(),newY-centerMarkerOffsetY)
          if (self.vectorEnd != None):
            startYX = self.vectorEnd["coords"]["y"]
            startYY = self.vectorEnd["coords"]["z"]
            newY = self.calculateNewYCoordPos(startYX,startYY)
            self.vectorEnd["graphicsitem"].setPos(self.vectorEnd["graphicsitem"].x(),newY-centerMarkerOffsetY)
        if (self.vectorEnd != None):
          self.vecLine.setLine(self.vectorStart["graphicsitem"].x()+self.vectorStart["centerCursorX"]+self.centerMarkerCharOffsetX,self.vectorStart["graphicsitem"].y()+self.vectorStart["centerCursorY"]+self.centerMarkerCharOffsetY,self.vectorEnd["graphicsitem"].x()+self.vectorStart["centerCursorX"]+self.centerMarkerCharOffsetX,self.vectorEnd["graphicsitem"].y()+self.vectorStart["centerCursorY"]+self.centerMarkerCharOffsetY)

    def queueEnScanCB(self):
      self.protoComboBox.setCurrentIndex(self.protoComboBox.findText(str("eScan")))      
      self.addRequestsToAllSelectedCB()
      self.treeChanged_pv.put(1)      

    def clearEnScanPlotCB(self):
      self.EScanGraph.removeCurves()     
      self.choochGraph.removeCurves()

    def displayXrecRaster(self,xrecRasterFlag):
      self.xrecRasterFlag_pv.put("0")
      if (xrecRasterFlag=="100"):
        for i in range(len(self.rasterList)):
          if (self.rasterList[i] != None):
            self.scene.removeItem(self.rasterList[i]["graphicsItem"])
      else:
        logger.info("xrecrasterflag = ")
        logger.info(xrecRasterFlag)
        rasterReq = db_lib.getRequestByID(xrecRasterFlag)
        rasterDef = rasterReq["request_obj"]["rasterDef"]
        if (rasterDef["status"] == 1):
          self.drawPolyRaster(rasterReq)
        elif (rasterDef["status"] == 2):
          if (self.controlEnabled()):          
            self.fillPolyRaster(rasterReq,takeSnapshot=True)
          else:
            self.fillPolyRaster(rasterReq,takeSnapshot=False)            
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
      self.gripperTempLabel.setText(str(gripVal))
      if (int(gripVal) > -170):
        self.gripperTempLabel.setStyleSheet("background-color: red;")        
      else:
        self.gripperTempLabel.setStyleSheet("background-color: #99FF66;")        

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
      self.EScanGraph.setTitle("Chooch PLot")
      self.EScanGraph.newcurve("whatever", graph_x, graph_y)
      self.EScanGraph.replot()
      chooch_graph_x = choochResultObj["choochOutXAxis"]
      chooch_graph_y1 = choochResultObj["choochOutY1Axis"]
      chooch_graph_y2 = choochResultObj["choochOutY2Axis"]      
      self.choochGraph.setTitle("Chooch PLot")
      self.choochGraph.newcurve("spline", chooch_graph_x, chooch_graph_y1)
      self.choochGraph.newcurve("fp", chooch_graph_x, chooch_graph_y2)
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
            self.totalExptime_ledit.setText(str(totalExptime))
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
        self.totalExptime_ledit.setText(str(totalExptime))
        if (str(self.protoComboBox.currentText()) == "vector"):
          try:
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
      self.resolution_ledit.setText(reso_s)
      
    def energyTextChanged(self,text):
      dist_s = "%.2f" % (daq_utils.distance_from_reso(daq_utils.det_radius,float(self.resolution_ledit.text()),float(text),0))
      self.detDistMotorEntry.getEntry().setText(dist_s)

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
        self.osc_range_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterDefaultWidth")))
        self.exp_time_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterDefaultTime")))
        self.transmission_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterDefaultTrans")))
      elif (protocol == "rasterScreen"):
        self.osc_start_ledit.setEnabled(False)
        self.osc_end_ledit.setEnabled(False)
        self.osc_range_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterDefaultWidth")))
        self.exp_time_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterDefaultTime")))
        self.transmission_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"rasterDefaultTrans")))
        self.protoOtherRadio.setChecked(True)        
      elif (protocol == "standard"):
        self.protoStandardRadio.setChecked(True)
        screenWidth = float(db_lib.getBeamlineConfigParam(daq_utils.beamline,"screen_default_width"))
        screenExptime = float(db_lib.getBeamlineConfigParam(daq_utils.beamline,"screen_default_time"))
        self.transmission_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"stdTrans")))
        self.osc_range_ledit.setText(str(screenWidth))
        self.exp_time_ledit.setText(str(screenExptime))
        self.osc_start_ledit.setEnabled(True)
        self.osc_end_ledit.setEnabled(True)
      elif (protocol == "burn"):
        self.fastDPCheckBox.setChecked(False)        
        screenWidth = float(db_lib.getBeamlineConfigParam(daq_utils.beamline,"burnDefaultNumFrames"))
        screenExptime = float(db_lib.getBeamlineConfigParam(daq_utils.beamline,"burnDefaultTime"))
        self.transmission_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"burnDefaultTrans")))
        self.osc_end_ledit.setText(str(screenWidth))
        self.exp_time_ledit.setText(str(screenExptime))
        self.osc_range_ledit.setText("0.0")
        self.osc_start_ledit.setEnabled(True)
        self.osc_end_ledit.setEnabled(True)
        
      elif (protocol == "vector"):
        screenWidth = float(db_lib.getBeamlineConfigParam(daq_utils.beamline,"screen_default_width"))
        screenExptime = float(db_lib.getBeamlineConfigParam(daq_utils.beamline,"screen_default_time"))
        self.transmission_ledit.setText(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"stdTrans")))        
        self.osc_range_ledit.setText(str(screenWidth))
        self.exp_time_ledit.setText(str(screenExptime))
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
      fname = QtGui.QFileDialog.getExistingDirectory(self, 'Choose Directory', '',QtGui.QFileDialog.DontUseNativeDialog)      
      if (fname != ""):
        self.dataPathGB.setBasePath_ledit(fname)


    def popImportDialogCB(self):
      self.timerHutch.stop()
      self.timerSample.stop()            
      fname = QtGui.QFileDialog.getOpenFileName(self, 'Choose Spreadsheet File', '',filter="*.xls *.xlsx",options=QtGui.QFileDialog.DontUseNativeDialog)
      self.timerSample.start(0)            
      self.timerHutch.start(500)            
      if (fname != ""):
        logger.info(fname)
        comm_s = "importSpreadsheet(\""+str(fname)+"\")"
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
      self.osc_start_ledit.setText(str(currentPos))
      
      
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
          self.rasterPoly = QtGui.QGraphicsPolygonItem(QtGui.QPolygonF(polyPoints))
        else:
          self.rasterPoly = QtGui.QGraphicsPolygonItem(QtGui.QPolygonF(self.click_positions))
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
      

    def fillPolyRaster(self,rasterReq,takeSnapshot=False): #at this point I should have a drawn polyRaster
      time.sleep(1)
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

      currentRasterGroup = self.rasterList[rasterListIndex]["graphicsItem"]
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
          else:
            if (rasterEvalOption == "Resolution"):
              try:
                color_id = int(255.0*(float(param-floor)/float(ceiling-floor)))
              except ZeroDivisionError:
                color_id = 0
            else:
              color_id = int(255-(255.0*(float(param-floor)/float(ceiling-floor))))
          self.currentRasterCellList[cellCounter].setBrush(QtGui.QBrush(QtGui.QColor(0,255-color_id,0,127)))
          self.currentRasterCellList[cellCounter].setData(0,spotcount)
          self.currentRasterCellList[cellCounter].setData(1,cellFilename)
          self.currentRasterCellList[cellCounter].setData(2,d_min)
          self.currentRasterCellList[cellCounter].setData(3,total_intensity)
          cellCounter+=1
      if (takeSnapshot):
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
        ispybLib.insertRasterResult(rasterResult,rasterReq,visitName)



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
              spotcount = currentRasterCellList[i].data(0).toInt()[0]
              my_array[cellIndex] = spotcount 
            elif (rasterEvalOption == "Intensity"):
              total_intensity  = currentRasterCellList[i].data(3).toInt()[0]
              my_array[cellIndex] = total_intensity
            else:
              d_min = currentRasterCellList[i].data(2).toDouble()[0]
              if (d_min == -1):
                d_min = 50.0 #trying to handle frames with no spots
              my_array[cellIndex] = d_min
          floor = np.amin(my_array)
          ceiling = np.amax(my_array)
          for i in range (0,len(currentRasterCellList)):
            if (rasterEvalOption == "Spot Count"):
              spotcount = currentRasterCellList[i].data(0).toInt()[0]
              param = spotcount 
            elif (rasterEvalOption == "Intensity"):
              total_intensity  = currentRasterCellList[i].data(3).toInt()[0]
              param = total_intensity
            else:
              d_min = currentRasterCellList[i].data(2).toDouble()[0]
              if (d_min == -1):
                d_min = 50.0 #trying to handle frames with no spots
              param = d_min
            if (ceiling == 0):
              color_id = 255
            if (rasterEvalOption == "Resolution"):
              color_id = int(255.0*(float(param-floor)/float(ceiling-floor)))
            else:
              color_id = int(255-(255.0*(float(param-floor)/float(ceiling-floor))))
            currentRasterCellList[i].setBrush(QtGui.QBrush(QtGui.QColor(0,255-color_id,0,127)))

      
        
    def saveCenterCB(self):
      pen = QtGui.QPen(QtCore.Qt.magenta)
      brush = QtGui.QBrush(QtCore.Qt.magenta)
      markWidth = 10
      marker = self.scene.addEllipse(self.centerMarker.x()-(markWidth/2.0)-1+self.centerMarkerCharOffsetX,self.centerMarker.y()-(markWidth/2.0)-1+self.centerMarkerCharOffsetY,markWidth,markWidth,pen,brush)
      marker.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)            
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
          
      beamWidth = float(self.beamWidth_ledit.text())
      beamHeight = float(self.beamHeight_ledit.text())
      if (self.scannerType == "PI"):
        rasterDef = {"rasterType":"normal","beamWidth":beamWidth,"beamHeight":beamHeight,"status":0,"x":self.sampx_pv.get()+self.sampFineX_pv.get(),"y":self.sampy_pv.get()+self.sampFineY_pv.get(),"z":self.sampz_pv.get()+self.sampFineZ_pv.get(),"omega":self.omega_pv.get(),"stepsize":stepsize,"rowDefs":[]} #just storing step as microns, not using her
      else:
        rasterDef = {"rasterType":"normal","beamWidth":beamWidth,"beamHeight":beamHeight,"status":0,"x":self.sampx_pv.get(),"y":self.sampy_pv.get(),"z":self.sampz_pv.get(),"omega":self.omega_pv.get(),"stepsize":stepsize,"rowDefs":[]} #just storing step as microns, not using here      
      numsteps_h = int(raster_w/stepsizeXPix) #raster_w = width,goes to numsteps horizonatl
      numsteps_v = int(raster_h/stepsizeYPix)
      if (numsteps_h == 2):
        numsteps_h = 1 #fix slop in user single line attempt
      if (numsteps_h%2 == 0): # make odd numbers of rows and columns
        numsteps_h = numsteps_h + 1
      if (numsteps_v%2 == 0):
        numsteps_v = numsteps_v + 1
      point_offset_x = -(numsteps_h*stepsizeXPix)/2
      point_offset_y = -(numsteps_v*stepsizeYPix)/2
      if ((numsteps_h == 1) or (numsteps_v > numsteps_h and db_lib.getBeamlineConfigParam(daq_utils.beamline,"vertRasterOn"))): #vertical raster
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
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterDefaultWidth",float(self.osc_range_ledit.text()))
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterDefaultTime",float(self.exp_time_ledit.text()))
      db_lib.setBeamlineConfigParam(daq_utils.beamline,"rasterDefaultTrans",float(self.transmission_ledit.text()))
      
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
      pen = QtGui.QPen(QtCore.Qt.green)
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
          newCell = RasterCell(newCellX,newCellY,stepsizeX, stepsizeY, self,self.scene)
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
        file = StringIO(urllib.urlopen(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"hutchCornerCamURL"))).read())
        img = Image.open(file)
        qimage = ImageQt.ImageQt(img)
        pixmap_orig = QtGui.QPixmap.fromImage(qimage)
        self.pixmap_item_HutchCorner.setPixmap(pixmap_orig)        
      except:
        pass
      try:
        file = StringIO(urllib.urlopen(str(db_lib.getBeamlineConfigParam(daq_utils.beamline,"hutchTopCamURL"))).read())
        img = Image.open(file)
        qimage = ImageQt.ImageQt(img)
        pixmap_orig = QtGui.QPixmap.fromImage(qimage)
        self.pixmap_item_HutchTop.setPixmap(pixmap_orig)
      except:
        pass
      

    def timerSampleRefresh(self):
      if self.capture is None:
        return 
      retval,self.readframe = self.capture.read()
      if self.readframe is None:
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
        super(QtGui.QGraphicsPixmapItem, self.pixmap_item).mousePressEvent(event)
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
        itemData = str(item.data(32).toString())
        itemDataType = str(item.data(33).toString())
        if (itemDataType == "request"): 
          self.selectedSampleRequest = db_lib.getRequestByID(itemData)
          self.editSampleRequestCB(singleRequest)
          singleRequest = 0
      self.treeChanged_pv.put(1)



    def editSampleRequestCB(self,singleRequest):
      colRequest=self.selectedSampleRequest
      reqObj = colRequest["request_obj"]
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
      progressInc = 100.0/float(len(indexes))
      self.progressDialog.setWindowTitle("Creating Requests")
      self.progressDialog.show()
      for i in range(len(indexes)):
        self.progressDialog.setValue(int((i+1)*progressInc))
        item = self.dewarTree.model.itemFromIndex(indexes[i])
        itemData = str(item.data(32).toString())
        itemDataType = str(item.data(33).toString())        
        if (itemDataType == "sample"): 
          self.selectedSampleID = itemData
          if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"queueCollect") == 0):
            if (self.mountedPin_pv.get() != self.selectedSampleID):                    
              self.popupServerMessage("You can only add requests to a mounted sample, for now.")
              self.progressDialog.close()              
              return
          
        self.selectedSampleRequest = daq_utils.createDefaultRequest(self.selectedSampleID) #7/21/15  - not sure what this does, b/c I don't pass it, ahhh probably the commented line for prefix
        if (len(indexes)>1):
          self.dataPathGB.setFilePrefix_ledit(str(self.selectedSampleRequest["request_obj"]["file_prefix"]))
          self.dataPathGB.setDataPath_ledit(str(self.selectedSampleRequest["request_obj"]["directory"]))
          self.EScanDataPathGBTool.setFilePrefix_ledit(str(self.selectedSampleRequest["request_obj"]["file_prefix"]))
          self.EScanDataPathGBTool.setDataPath_ledit(str(self.selectedSampleRequest["request_obj"]["directory"]))
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

      if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"queueCollect") == 0):
        if (self.mountedPin_pv.get() != self.selectedSampleID):                    
          self.popupServerMessage("You can only add requests to a mounted sample, for now.")
          return
        
#skinner, not pretty below the way stuff is duplicated.
      if ((float(self.osc_end_ledit.text()) < float(self.osc_range_ledit.text())) and str(self.protoComboBox.currentText()) != "eScan"):
        self.popupServerMessage("Osc range less than Osc width")
        return
      if (self.periodicTableTool.isVisible()): #this one is for periodicTableTool, the other block is periodicTable, 6/17 - we don't use tool anymore
        if (self.periodicTableTool.eltCurrent != None):
          symbol = self.periodicTableTool.eltCurrent.symbol
          targetEdge = element_info[symbol][2]
          targetEnergy = ElementsInfo.Elements.Element[symbol]["binding"][targetEdge]
          colRequest = daq_utils.createDefaultRequest(self.selectedSampleID)
          sampleName = str(db_lib.getSampleNamebyID(colRequest["sample"]))
          runNum = db_lib.incrementSampleRequestCount(colRequest["sample"])
          (puckPosition,samplePositionInContainer,containerID) = db_lib.getCoordsfromSampleID(daq_utils.beamline,colRequest["sample"])
          reqObj = get_request_object_escan(colRequest["request_obj"], self.periodicTable.eltCurrent.symbol, runNum, self.EScanDataPathGBTool.prefix_ledit.text(),
                                            self.EScanDataPathGBTool.base_path_ledit.text(), sampleName, containerID, samplePositionInContainer,
                                            self.EScanDataPathGBTool.file_numstart_ledit.text(), self.exp_time_ledit.text(), targetEnergy, self.escan_steps_ledit.text(),
                                            self.escan_stepsize_ledit.text())
          colRequest["request_obj"] = reqObj
          newSampleRequestID = db_lib.addRequesttoSample(self.selectedSampleID,reqObj["protocol"],daq_utils.owner,reqObj,priority=5000,proposalID=daq_utils.getProposalID())
#attempt here to select a newly created request.        
          self.SelectedItemData = newSampleRequestID
          newSampleRequest = db_lib.getRequestByID(newSampleRequestID)
          
          if (selectedSampleID == None): #this is a temp kludge to see if this is called from addAll
            self.treeChanged_pv.put(1)
        else:
          logger.info("choose an element and try again")
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
          targetEnergy = ElementsInfo.Elements.Element[symbol]["binding"][targetEdge]
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
             db_lib.setBeamlineConfigParam(daq_utils.beamline,"screen_default_width",float(self.osc_range_ledit.text()))
             db_lib.setBeamlineConfigParam(daq_utils.beamline,"screen_default_time",float(self.exp_time_ledit.text()))
             db_lib.setBeamlineConfigParam(daq_utils.beamline,"stdTrans",float(self.transmission_ledit.text()))
             db_lib.setBeamlineConfigParam(daq_utils.beamline,"screen_default_dist",float(self.detDistMotorEntry.getEntry().text()))
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
          message = QtGui.QErrorMessage(self)
          message.setModal(False)
          message.showMessage("You need to select a centering.")
      else: #autocenter or interactive
        colRequest=self.selectedSampleRequest
        sampleName = str(db_lib.getSampleNamebyID(colRequest["sample"]))
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
          db_lib.setBeamlineConfigParam(daq_utils.beamline,"screen_default_width",float(self.osc_range_ledit.text()))
          db_lib.setBeamlineConfigParam(daq_utils.beamline,"screen_default_time",float(self.exp_time_ledit.text()))
          db_lib.setBeamlineConfigParam(daq_utils.beamline,"stdTrans",float(self.transmission_ledit.text()))
          db_lib.setBeamlineConfigParam(daq_utils.beamline,"screen_default_dist",float(self.detDistMotorEntry.getEntry().text()))          
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
          try:
            totalExpTime =(float(self.osc_end_ledit.text())/float(self.osc_range_ledit.text()))*float(self.exp_time_ledit.text()) #(range/inc)*exptime
            speed = trans_total/totalExpTime
            self.vecSpeedLabelOutput.setText(str(int(speed)))
          except:
            pass
          framesPerPoint = int(self.vectorFPP_ledit.text())
          vectorParams={"vecStart":self.vectorStart["coords"],"vecEnd":self.vectorEnd["coords"],"x_vec":x_vec,"y_vec":y_vec,"z_vec":z_vec,"trans_total":trans_total,"fpp":framesPerPoint}
          reqObj["vectorParams"] = vectorParams
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

    def cooldownGripperCB(self):
      self.send_to_server("cooldownGripper()")      

    def parkGripperCB(self):
      self.send_to_server("parkGripper()")      
      
    def restartServerCB(self):
      if (self.controlEnabled()):
        msg = "Desperation move. Are you sure?"
        self.timerHutch.stop()
        self.timerSample.stop()      
        reply = QtGui.QMessageBox.question(self, 'Message',msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        self.timerSample.start(0)            
        self.timerHutch.start(500)      
        if reply == QtGui.QMessageBox.Yes:
          if (daq_utils.beamline == "fmx"):  #TODO replace with directly getting hostname
            os.system("ssh -q -X xf17id1-ca1 \"cd " + os.getcwd() + ";xterm -e /usr/local/bin/lsdcServer\"&")
          else:
            os.system("ssh -q -X xf17id2-ca1 \"cd " + os.getcwd() + ";xterm -e /usr/local/bin/lsdcServer\"&")
      else:
        self.popupServerMessage("You don't have control")
          

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
      self.timerHutch.start(500)            
      

    def setVectorStartCB(self): #save sample x,y,z
      if (self.vectorStart != None):
        self.scene.removeItem(self.vectorStart["graphicsitem"])
        self.vectorStart = None
      pen = QtGui.QPen(QtCore.Qt.blue)
      brush = QtGui.QBrush(QtCore.Qt.blue)
      markWidth = 10      
      vecStartMarker = self.scene.addEllipse(self.centerMarker.x()-(markWidth/2.0)-1+self.centerMarkerCharOffsetX,self.centerMarker.y()-(markWidth/2.0)-1+self.centerMarkerCharOffsetY,markWidth,markWidth,pen,brush)
      vectorStartcoords = {"x":self.sampx_pv.get(),"y":self.sampy_pv.get(),"z":self.sampz_pv.get()}
      self.vectorStart = {"coords":vectorStartcoords,"graphicsitem":vecStartMarker,"centerCursorX":self.centerMarker.x(),"centerCursorY":self.centerMarker.y()}



    def setVectorEndCB(self): #save sample x,y,z
      if (self.vectorEnd != None):
        self.scene.removeItem(self.vectorEnd["graphicsitem"])
        self.scene.removeItem(self.vecLine)
        self.vectorEnd = None
        
      pen = QtGui.QPen(QtCore.Qt.blue)
      brush = QtGui.QBrush(QtCore.Qt.blue)
      markWidth = 10            
      vecEndMarker = self.scene.addEllipse(self.centerMarker.x()-(markWidth/2.0)-1+self.centerMarkerCharOffsetX,self.centerMarker.y()-(markWidth/2.0)-1+self.centerMarkerCharOffsetY,markWidth,markWidth,pen,brush)
      vectorEndcoords = {"x":self.sampx_pv.get(),"y":self.sampy_pv.get(),"z":self.sampz_pv.get()}
      self.vectorEnd = {"coords":vectorEndcoords,"graphicsitem":vecEndMarker,"centerCursorX":self.centerMarker.x(),"centerCursorY":self.centerMarker.y()}
      try:
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
      except:
        pass
      self.protoVectorRadio.setChecked(True)
      self.vecLine = self.scene.addLine(self.centerMarker.x()+self.vectorStart["graphicsitem"].x()+self.centerMarkerCharOffsetX,self.centerMarker.y()+self.vectorStart["graphicsitem"].y()+self.centerMarkerCharOffsetY,self.centerMarker.x()+vecEndMarker.x()+self.centerMarkerCharOffsetX,self.centerMarker.y()+vecEndMarker.y()+self.centerMarkerCharOffsetY, pen)
      self.vecLine.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)

    def clearVectorCB(self):
      if (self.vectorStart != None):
        self.scene.removeItem(self.vectorStart["graphicsitem"])
        self.vectorStart = None
      if (self.vectorEnd != None):
        self.scene.removeItem(self.vectorEnd["graphicsitem"])
        self.scene.removeItem(self.vecLine)
        self.vectorEnd = None
        self.vecLenLabelOutput.setText("---")
        self.vecSpeedLabelOutput.setText("---")        

    def puckToDewarCB(self):
      while (1):
        self.timerHutch.stop()
        self.timerSample.stop()      
        puckName, ok = PuckDialog.getPuckName()
        self.timerSample.start(0)            
        self.timerHutch.start(500)      
        if (ok):
          self.timerHutch.stop()
          self.timerSample.stop()      
          dewarPos, ok = DewarDialog.getDewarPos(parent=self,action="add")
          self.timerSample.start(0)            
          self.timerHutch.start(500)      
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
      if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"mountEnabled") == 0):
        self.popupServerMessage("Mounting disabled!! Call staff!")
        return
      logger.info("mount selected sample")
      self.eraseCB()      
      self.selectedSampleID = self.selectedSampleRequest["sample"]
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
      
      self.osc_start_ledit.setText(str(reqObj["sweep_start"]))
      self.osc_end_ledit.setText(str(reqObj["sweep_end"]-reqObj["sweep_start"]))
      self.osc_range_ledit.setText(str(reqObj["img_width"]))
      self.exp_time_ledit.setText(str(reqObj["exposure_time"]))
      self.resolution_ledit.setText(str(reqObj["resolution"]))
      self.dataPathGB.setFileNumstart_ledit(str(reqObj["file_number_start"]))
      self.beamWidth_ledit.setText(str(reqObj["slit_width"]))
      self.beamHeight_ledit.setText(str(reqObj["slit_height"]))
      self.transmission_ledit.setText(str(reqObj["attenuation"]))
      if (reqObj.has_key("fastDP")):
        self.fastDPCheckBox.setChecked((reqObj["fastDP"] or reqObj["fastEP"] or reqObj["dimple"]))
      if (reqObj.has_key("fastEP")):
        self.fastEPCheckBox.setChecked(reqObj["fastEP"])
      if (reqObj.has_key("dimple")):
        self.dimpleCheckBox.setChecked(reqObj["dimple"])        
      if (reqObj.has_key("xia2")):
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
        if (selectedSampleRequest.has_key("priority")):
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
          self.fillPolyRaster(selectedSampleRequest,takeSnapshot=False)
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
      puck_name = parent.data().toString()
      itemData = str(item.data(32).toString())
      itemDataType = str(item.data(33).toString())
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
            self.osc_range_ledit.setText("0.0")
          reqObj = self.selectedSampleRequest["request_obj"]
          self.dataPathGB.setFilePrefix_ledit(str(reqObj["file_prefix"]))          
          self.dataPathGB.setBasePath_ledit(reqObj["basePath"])
          self.dataPathGB.setDataPath_ledit(reqObj["directory"])
          self.EScanDataPathGBTool.setFilePrefix_ledit(str(reqObj["file_prefix"]))          
          self.EScanDataPathGBTool.setBasePath_ledit(reqObj["basePath"])
          self.EScanDataPathGBTool.setDataPath_ledit(reqObj["directory"])
          self.EScanDataPathGBTool.setFileNumstart_ledit(str(reqObj["file_number_start"]))          
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
            self.osc_range_ledit.setText("0.0")
        else:
          self.selectedSampleRequest = daq_utils.createDefaultRequest(itemData,createVisit=False)
          reqObj = self.selectedSampleRequest["request_obj"]
          self.dataPathGB.setFilePrefix_ledit(str(reqObj["file_prefix"]))          
          self.dataPathGB.setBasePath_ledit(reqObj["basePath"])
          self.dataPathGB.setDataPath_ledit(reqObj["directory"])
          self.EScanDataPathGBTool.setFilePrefix_ledit(str(reqObj["file_prefix"]))          
          self.EScanDataPathGBTool.setBasePath_ledit(reqObj["basePath"])
          self.EScanDataPathGBTool.setDataPath_ledit(reqObj["directory"])
          self.EScanDataPathGBTool.setFileNumstart_ledit(str(reqObj["file_number_start"]))          
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
          if (reqObj["runChooch"]):
            resultList = db_lib.getResultsforRequest(reqID)
            if (len(resultList) > 0):
              lastResult = resultList[-1]
              if (db_lib.getResult(lastResult['uid'])["result_type"] == "choochResult"):                  
                resultID = lastResult['uid']
                logger.info("plotting chooch")
                self.processChoochResult(resultID)
        self.refreshCollectionParams(self.selectedSampleRequest)


    def processXrecRasterCB(self,value=None, char_value=None, **kw):
      xrecFlag = value
      if (xrecFlag != "0"):
        self.emit(QtCore.SIGNAL("xrecRasterSignal"),xrecFlag)

    def processChoochResultsCB(self,value=None, char_value=None, **kw):
      choochFlag = value
      if (choochFlag != "0"):
        self.emit(QtCore.SIGNAL("choochResultSignal"),choochFlag)

    def processEnergyChangeCB(self,value=None, char_value=None, **kw):
      energyVal = value
      self.emit(QtCore.SIGNAL("energyChangeSignal"),energyVal)

    def mountedPinChangedCB(self,value=None, char_value=None, **kw):
      mountedPinPos = value
      self.emit(QtCore.SIGNAL("mountedPinSignal"),mountedPinPos)

    def beamSizeChangedCB(self,value=None, char_value=None, **kw):
      beamSizeFlag = value
      self.emit(QtCore.SIGNAL("beamSizeSignal"),beamSizeFlag)
    
    def controlMasterChangedCB(self,value=None, char_value=None, **kw):
      controlMasterPID = value
      self.emit(QtCore.SIGNAL("controlMasterSignal"),controlMasterPID)

    def zebraArmStateChangedCB(self,value=None, char_value=None, **kw):
      armState = value
      self.emit(QtCore.SIGNAL("zebraArmStateSignal"),armState)
      
    def govRobotSeReachChangedCB(self,value=None, char_value=None, **kw):
      armState = value
      self.emit(QtCore.SIGNAL("govRobotSeReachSignal"),armState)

    def govRobotSaReachChangedCB(self,value=None, char_value=None, **kw):
      armState = value
      self.emit(QtCore.SIGNAL("govRobotSaReachSignal"),armState)

    def govRobotDaReachChangedCB(self,value=None, char_value=None, **kw):
      armState = value
      self.emit(QtCore.SIGNAL("govRobotDaReachSignal"),armState)

    def govRobotBlReachChangedCB(self,value=None, char_value=None, **kw):
      armState = value
      self.emit(QtCore.SIGNAL("govRobotBlReachSignal"),armState)      


    def detMessageChangedCB(self,value=None, char_value=None, **kw):
      state = char_value
      self.emit(QtCore.SIGNAL("detMessageSignal"),state)
      
    def sampleFluxChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.emit(QtCore.SIGNAL("sampleFluxSignal"),state)
      
    def zebraPulseStateChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.emit(QtCore.SIGNAL("zebraPulseStateSignal"),state)

    def stillModeStateChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.emit(QtCore.SIGNAL("stillModeStateSignal"),state)

    def zebraDownloadStateChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.emit(QtCore.SIGNAL("zebraDownloadStateSignal"),state)

    def zebraSentTriggerStateChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.emit(QtCore.SIGNAL("zebraSentTriggerStateSignal"),state)
      
    def zebraReturnedTriggerStateChangedCB(self,value=None, char_value=None, **kw):
      state = value
      self.emit(QtCore.SIGNAL("zebraReturnedTriggerStateSignal"),state)
      
    def shutterChangedCB(self,value=None, char_value=None, **kw):
      shutterVal = value        
      self.emit(QtCore.SIGNAL("fastShutterSignal"),shutterVal)
      
    def gripTempChangedCB(self,value=None, char_value=None, **kw):
      gripVal = value        
      self.emit(QtCore.SIGNAL("gripTempSignal"),gripVal)

    def ringCurrentChangedCB(self,value=None, char_value=None, **kw):
      ringCurrentVal = value        
      self.emit(QtCore.SIGNAL("ringCurrentSignal"),ringCurrentVal)

    def beamAvailableChangedCB(self,value=None, char_value=None, **kw):
      beamAvailableVal = value        
      self.emit(QtCore.SIGNAL("beamAvailableSignal"),beamAvailableVal)

    def sampleExposedChangedCB(self,value=None, char_value=None, **kw):
      sampleExposedVal = value        
      self.emit(QtCore.SIGNAL("sampleExposedSignal"),sampleExposedVal)
      
    def processSampMoveCB(self,value=None, char_value=None, **kw):
      posRBV = value
      motID = kw["motID"]
      self.emit(QtCore.SIGNAL("sampMoveSignal"),posRBV,motID)

    def processROIChangeCB(self,value=None, char_value=None, **kw):
      posRBV = value
      ID = kw["ID"]
      self.emit(QtCore.SIGNAL("roiChangeSignal"),posRBV,ID)
      

    def processHighMagCursorChangeCB(self,value=None, char_value=None, **kw):
      posRBV = value
      ID = kw["ID"]
      self.emit(QtCore.SIGNAL("highMagCursorChangeSignal"),posRBV,ID)
      
    def processLowMagCursorChangeCB(self,value=None, char_value=None, **kw):
      posRBV = value
      ID = kw["ID"]
      self.emit(QtCore.SIGNAL("lowMagCursorChangeSignal"),posRBV,ID)
      

    def treeChangedCB(self,value=None, char_value=None, **kw):
      if (self.processID != self.treeChanged_pv.get()):
        self.emit(QtCore.SIGNAL("refreshTreeSignal"))

    def serverMessageCB(self,value=None, char_value=None, **kw):
      serverMessageVar = char_value
      self.emit(QtCore.SIGNAL("serverMessageSignal"),serverMessageVar)

    def serverPopupMessageCB(self,value=None, char_value=None, **kw):
      serverMessageVar = char_value
      self.emit(QtCore.SIGNAL("serverPopupMessageSignal"),serverMessageVar)

      
    def programStateCB(self, value=None, char_value=None, **kw):
      programStateVar = value
      self.emit(QtCore.SIGNAL("programStateSignal"),programStateVar)

    def pauseButtonStateCB(self, value=None, char_value=None, **kw):
      pauseButtonStateVar = value
      self.emit(QtCore.SIGNAL("pauseButtonStateSignal"),pauseButtonStateVar)

        
    def initUI(self):               
        self.tabs= QtGui.QTabWidget()
        self.comm_pv = PV(daq_utils.beamlineComm + "command_s")
        self.immediate_comm_pv = PV(daq_utils.beamlineComm + "immediate_command_s")
        self.stillModeStatePV = PV(daq_utils.pvLookupDict["stillModeStatus"])        
        self.progressDialog = QtGui.QProgressDialog()
        self.progressDialog.setCancelButtonText(QtCore.QString())
        self.progressDialog.setModal(False)
        tab1= QtGui.QWidget()
        vBoxlayout1= QtGui.QVBoxLayout()
        splitter1 = QtGui.QSplitter(QtCore.Qt.Vertical,self)
        splitter1.addWidget(self.tabs)
        self.setCentralWidget(splitter1)
        splitterSizes = [600,100]
        importAction = QtGui.QAction('Import Spreadsheet...', self)
        importAction.triggered.connect(self.popImportDialogCB)
        modeGroup = QActionGroup(self);
        modeGroup.setExclusive(True)        
        self.userAction = QtGui.QAction('User Mode', self,checkable=True)
        self.userAction.triggered.connect(self.setUserModeCB)
        self.userAction.setChecked(True)
        self.expertAction = QtGui.QAction('Expert Mode', self,checkable=True)
        self.expertAction.triggered.connect(self.setExpertModeCB)
        self.staffAction = QtGui.QAction('Staff Panel...', self)
        self.staffAction.triggered.connect(self.popStaffDialogCB)
        modeGroup.addAction(self.userAction)
        modeGroup.addAction(self.expertAction)
        exitAction = QtGui.QAction(QtGui.QIcon('exit24.png'), 'Exit', self)
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
        self.setWindowTitle('LSDC')    
        self.show()

    def popStaffDialogCB(self):
      if (self.controlEnabled()):
        self.staffScreenDialog = StaffScreenDialog(self)
      else:
        self.popupServerMessage("You don't have control")          
      

    def closeAll(self):
      QtGui.QApplication.closeAllWindows()


    def initCallbacks(self):

      self.connect(self, QtCore.SIGNAL("beamSizeSignal"),self.processBeamSize)
      self.beamSize_pv.add_callback(self.beamSizeChangedCB)  

      self.treeChanged_pv = PV(daq_utils.beamlineComm + "live_q_change_flag")
      self.connect(self, QtCore.SIGNAL("refreshTreeSignal"),self.dewarTree.refreshTree)
      self.treeChanged_pv.add_callback(self.treeChangedCB)  
      self.mountedPin_pv = PV(daq_utils.beamlineComm + "mounted_pin")
      self.connect(self, QtCore.SIGNAL("mountedPinSignal"),self.processMountedPin)
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
      self.connect(self, QtCore.SIGNAL("zebraArmStateSignal"),self.processZebraArmState)
      self.zebraArmedPV.add_callback(self.zebraArmStateChangedCB)

      self.govRobotSeReachPV = PV(daq_utils.pvLookupDict["govRobotSeReach"])
      self.connect(self, QtCore.SIGNAL("govRobotSeReachSignal"),self.processGovRobotSeReach)
      self.govRobotSeReachPV.add_callback(self.govRobotSeReachChangedCB)

      self.govRobotSaReachPV = PV(daq_utils.pvLookupDict["govRobotSaReach"])
      self.connect(self, QtCore.SIGNAL("govRobotSaReachSignal"),self.processGovRobotSaReach)
      self.govRobotSaReachPV.add_callback(self.govRobotSaReachChangedCB)

      self.govRobotDaReachPV = PV(daq_utils.pvLookupDict["govRobotDaReach"])
      self.connect(self, QtCore.SIGNAL("govRobotDaReachSignal"),self.processGovRobotDaReach)
      self.govRobotDaReachPV.add_callback(self.govRobotDaReachChangedCB)

      self.govRobotBlReachPV = PV(daq_utils.pvLookupDict["govRobotBlReach"])
      self.connect(self, QtCore.SIGNAL("govRobotBlReachSignal"),self.processGovRobotBlReach)
      self.govRobotBlReachPV.add_callback(self.govRobotBlReachChangedCB)
      
      self.detectorMessagePV = PV(daq_utils.pvLookupDict["eigerStatMessage"])
      self.connect(self, QtCore.SIGNAL("detMessageSignal"),self.processDetMessage)
      self.detectorMessagePV.add_callback(self.detMessageChangedCB)


      self.connect(self, QtCore.SIGNAL("sampleFluxSignal"),self.processSampleFlux)
      self.sampleFluxPV.add_callback(self.sampleFluxChangedCB)
      
      self.connect(self, QtCore.SIGNAL("stillModeStateSignal"),self.processStillModeState)
      self.stillModeStatePV.add_callback(self.stillModeStateChangedCB)      

      self.zebraPulsePV = PV(daq_utils.pvLookupDict["zebraPulseStatus"])
      self.connect(self, QtCore.SIGNAL("zebraPulseStateSignal"),self.processZebraPulseState)
      self.zebraPulsePV.add_callback(self.zebraPulseStateChangedCB)

      self.zebraDownloadPV = PV(daq_utils.pvLookupDict["zebraDownloading"])
      self.connect(self, QtCore.SIGNAL("zebraDownloadStateSignal"),self.processZebraDownloadState)
      self.zebraDownloadPV.add_callback(self.zebraDownloadStateChangedCB)

      self.zebraSentTriggerPV = PV(daq_utils.pvLookupDict["zebraSentTriggerStatus"])
      self.connect(self, QtCore.SIGNAL("zebraSentTriggerStateSignal"),self.processZebraSentTriggerState)
      self.zebraSentTriggerPV.add_callback(self.zebraSentTriggerStateChangedCB)

      self.zebraReturnedTriggerPV = PV(daq_utils.pvLookupDict["zebraTriggerReturnStatus"])
      self.connect(self, QtCore.SIGNAL("zebraReturnedTriggerStateSignal"),self.processZebraReturnedTriggerState)
      self.zebraReturnedTriggerPV.add_callback(self.zebraReturnedTriggerStateChangedCB)
      
      self.controlMaster_pv = PV(daq_utils.beamlineComm + "zinger_flag")
      self.connect(self, QtCore.SIGNAL("controlMasterSignal"),self.processControlMaster)
      self.controlMaster_pv.add_callback(self.controlMasterChangedCB)

      self.beamCenterX_pv = PV(daq_utils.pvLookupDict["beamCenterX"])
      self.beamCenterY_pv = PV(daq_utils.pvLookupDict["beamCenterY"])      

      self.choochResultFlag_pv = PV(daq_utils.beamlineComm + "choochResultFlag")
      self.connect(self, QtCore.SIGNAL("choochResultSignal"),self.processChoochResult)
      self.choochResultFlag_pv.add_callback(self.processChoochResultsCB)  
      self.xrecRasterFlag_pv = PV(daq_utils.beamlineComm + "xrecRasterFlag")
      self.xrecRasterFlag_pv.put("0")
      self.connect(self, QtCore.SIGNAL("xrecRasterSignal"),self.displayXrecRaster)
      self.xrecRasterFlag_pv.add_callback(self.processXrecRasterCB)  
      self.message_string_pv = PV(daq_utils.beamlineComm + "message_string") 
      self.connect(self, QtCore.SIGNAL("serverMessageSignal"),self.printServerMessage)
      self.message_string_pv.add_callback(self.serverMessageCB)  
      self.popup_message_string_pv = PV(daq_utils.beamlineComm + "gui_popup_message_string") 
      self.connect(self, QtCore.SIGNAL("serverPopupMessageSignal"),self.popupServerMessage)
      self.popup_message_string_pv.add_callback(self.serverPopupMessageCB)  
      self.program_state_pv = PV(daq_utils.beamlineComm + "program_state") 
      self.connect(self, QtCore.SIGNAL("programStateSignal"),self.colorProgramState)
      self.program_state_pv.add_callback(self.programStateCB)  
      self.pause_button_state_pv = PV(daq_utils.beamlineComm + "pause_button_state") 
      self.connect(self, QtCore.SIGNAL("pauseButtonStateSignal"),self.changePauseButtonState)
      self.pause_button_state_pv.add_callback(self.pauseButtonStateCB)  

      self.connect(self, QtCore.SIGNAL("energyChangeSignal"),self.processEnergyChange)
      self.energy_pv.add_callback(self.processEnergyChangeCB,motID="x")

      self.sampx_pv = PV(daq_utils.motor_dict["sampleX"]+".RBV")      
      self.connect(self, QtCore.SIGNAL("sampMoveSignal"),self.processSampMove)
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
      self.connect(self, QtCore.SIGNAL("fastShutterSignal"),self.processFastShutter)      
      self.fastShutterRBV_pv.add_callback(self.shutterChangedCB)
      self.connect(self, QtCore.SIGNAL("gripTempSignal"),self.processGripTemp)      
      self.gripTemp_pv.add_callback(self.gripTempChangedCB)
      self.connect(self, QtCore.SIGNAL("ringCurrentSignal"),self.processRingCurrent)      
      self.ringCurrent_pv.add_callback(self.ringCurrentChangedCB)
      self.connect(self, QtCore.SIGNAL("beamAvailableSignal"),self.processBeamAvailable)      
      self.beamAvailable_pv.add_callback(self.beamAvailableChangedCB)
      self.connect(self, QtCore.SIGNAL("sampleExposedSignal"),self.processSampleExposed)      
      self.sampleExposed_pv.add_callback(self.sampleExposedChangedCB)
      self.connect(self, QtCore.SIGNAL("highMagCursorChangeSignal"),self.processHighMagCursorChange)
      self.highMagCursorX_pv.add_callback(self.processHighMagCursorChangeCB,ID="x")
      self.highMagCursorY_pv.add_callback(self.processHighMagCursorChangeCB,ID="y")      
      self.connect(self, QtCore.SIGNAL("lowMagCursorChangeSignal"),self.processLowMagCursorChange)
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
    reqObj["file_number_start"] = int(file_number_start)
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
    app = QtGui.QApplication(sys.argv)
    ex = controlMain()
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
