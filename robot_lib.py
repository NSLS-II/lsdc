#this will evolve for the staubli. Will need to know currently mounted sample. Will need to store this in the db.
#import staubliEpicsLib
#import stateModule

import RobotControlLib
import daq_utils
import db_lib
from daq_utils import getBlConfig
import daq_lib
import beamline_lib
import time
import daq_macros
import beamline_support
from beamline_support import getPvValFromDescriptor as getPvDesc, setPvValFromDescriptor as setPvDesc
import os
import filecmp
import _thread
import logging
from config_params import TOP_VIEW_CHECK
logger = logging.getLogger(__name__)

global method_pv,var_pv,pinsPerPuck
pinsPerPuck = 16

global sampXadjust, sampYadjust, sampZadjust
sampXadjust = 0
sampYadjust = 0
sampZadjust = 0

global retryMountCount
retryMountCount = 0

def finish():
  if (getBlConfig('robot_online')):  
    try:
      RobotControlLib.runCmd("finish")
      return 1    
    except Exception as e:
      e_s = str(e)
      message = "ROBOT Finish ERROR: " + e_s
      daq_lib.gui_message(message)
      logger.error(message)
      return 0

def warmupGripperRecoverThread(savedThreshold,junk):
  time.sleep(120.0)
  setPvDesc("warmupThreshold",savedThreshold)      

def wait90TopviewThread(prefix1,prefix90):
  global sampXadjust, sampYadjust, sampZadjust

  sampXadjust = 0
  sampYadjust = 0
  sampZadjust = 0
  startTime = time.time()
  if (getPvDesc("gripTemp")>-170):
    threadTimeout = 130.0
  else:
    threadTimeout = 30.0    
  while (1):
    omegaCP = beamline_lib.motorPosFromDescriptor("omega")
    if (omegaCP > 89.5 and omegaCP < 90.5):
      logger.info("leaving topview thread for 90")      
      break
    if (time.time()-startTime > threadTimeout):
      logger.info("leaving topview thread for " + str(threadTimeout))
      setPvDesc("topViewTrigMode",0)    
      setPvDesc("topViewImMode",2)
      setPvDesc("topViewDataType",1)
      setPvDesc("topViewAcquire",1,wait=False)    
      return
    time.sleep(0.10)
  try:
    daq_macros.topViewWrite()
    daq_macros.topViewSnap(prefix90,os.getcwd()+"/pinAlign",1)
    snapshot1Name = prefix1+"_001.jpg"
    snapshot2Name = prefix90+"_001.jpg"
    if (not filecmp.cmp(os.getcwd()+"/pinAlign/"+snapshot1Name,os.getcwd()+"/pinAlign/"+snapshot2Name)): #this would mean something is wrong if true because the pictures are identical
      comm_s = os.environ["LSDCHOME"] + "/runPinAlign.py " + snapshot1Name + " " + snapshot2Name
      logger.info(comm_s)
      lines = os.popen(comm_s).readlines()
      logger.info("printing lines right after popen ")
      logger.info(lines)
      logger.info(" done")
      if (lines[0].find("CANNOT CENTER") == -1):
        offsetTokens = lines[0].split()
        logger.info(offsetTokens[0] + " " + offsetTokens[1] + " " + offsetTokens[2])
        xlimLow = getPvDesc("robotXMountPos") + getPvDesc("robotXMountLowLim")
        xlimHi = getPvDesc("robotXMountPos") + getPvDesc("robotXMountHiLim")
        xpos = beamline_lib.motorPosFromDescriptor("sampleX")          
        target = xpos + float(offsetTokens[0])*1000.0
        if (target<xlimLow or target>xlimHi):
          logger.info("Pin X move beyond limit - Mount next sample.")
##else it thinks it worked              return 0
        else:
          sampXadjust = 1000.0*float(offsetTokens[0])
          sampYadjust = 1000.0*float(offsetTokens[1])
          sampZadjust = 1000.0*float(offsetTokens[2])
          sampXCP = beamline_lib.motorPosFromDescriptor("sampleX")
          sampYCP = beamline_lib.motorPosFromDescriptor("sampleY")
          sampZCP = beamline_lib.motorPosFromDescriptor("sampleZ")
          sampXAbsolute = sampXCP+sampXadjust          
          sampYAbsolute = sampYCP+sampYadjust          
          sampZAbsolute = sampZCP+sampZadjust
          setPvDesc("robotXWorkPos",sampXAbsolute)
          setPvDesc("robotYWorkPos",sampYAbsolute)
          setPvDesc("robotZWorkPos",sampZAbsolute)          
      else:
        logger.info("Cannot align pin - Mount next sample.")
#else it thinks it worked            return 0
      for outputline in lines:
        logger.info(outputline)
  except Exception as e:
    e_s = str(e)
    message = "TopView check ERROR, will continue: " + e_s
    daq_lib.gui_message(message)
    logger.error(message)
    
  
  
def recoverRobot():
  try:
    rebootEMBL()
    time.sleep(8.0)    
    RobotControlLib.runCmd("recover")
  except Exception as e:
    e_s = str(e)
    daq_lib.gui_message("ROBOT Recover failed! " + e_s)            


def dryGripper():
  try:
    saveThreshold = getPvDesc("warmupThresholdRBV")
    setPvDesc("warmupThreshold",50)
    _thread.start_new_thread(warmupGripperRecoverThread,(saveThreshold,0))
    warmupGripperForDry()
  except Exception as e:
    e_s = str(e)
    daq_lib.gui_message("Dry gripper failed! " + e_s)
    setPvDesc("warmupThreshold",saveThreshold)          
    
def DewarAutoFillOn():
  RobotControlLib.runCmd("turnOnAutoFill")

def DewarAutoFillOff():
  RobotControlLib.runCmd("turnOffAutoFill")

def DewarHeaterOn():
  RobotControlLib.runCmd("dewarHeaterOn")
  
def DewarHeaterOff():
  RobotControlLib.runCmd("dewarHeaterOff")


def warmupGripper():
  try:
    RobotControlLib.runCmd("warmupGripper")
    daq_lib.mountCounter = 0    
  except:
    daq_lib.gui_message("ROBOT warmup failed!")            

def warmupGripperForDry():

    RobotControlLib.runCmd("warmupGripper")
    daq_lib.mountCounter = 0    
    


def enableDewarTscreen():
  RobotControlLib.runCmd("enableTScreen")
  
def openPort(portNo):
  RobotControlLib.openPort(int(portNo))

def closePorts():
  RobotControlLib.runCmd("closePorts")
  
def rebootEMBL():
  RobotControlLib.rebootEMBL()
  
def cooldownGripper():
  try:
    RobotControlLib.runCmd("cooldownGripper")
  except:
    daq_lib.gui_message("ROBOT cooldown failed!")            
    

def parkGripper():
  try:
    RobotControlLib.runCmd("park")
  except Exception as e:
    e_s = str(e)
    message = "Park gripper Failed!: " + e_s
    daq_lib.gui_message(message)
    logger.error(message)
    

def setWorkposThread(init,junk):
  logger.info("setting work pos in thread")
  setPvDesc("robotGovActive",1)
  setPvDesc("robotXWorkPos",getPvDesc("robotXMountPos"))
  setPvDesc("robotYWorkPos",getPvDesc("robotYMountPos"))
  setPvDesc("robotZWorkPos",getPvDesc("robotZMountPos"))
  setPvDesc("robotOmegaWorkPos",90.0)
  if (init):
    time.sleep(20)
    setPvDesc("robotGovActive",0)      

def testRobot():
  try:
    RobotControlLib.testRobot()
    logger.info("Test Robot passed!")
    daq_lib.gui_message("Test Robot passed!")
  except Exception as e:
    e_s = str(e)
    message = "Test Robot failed!: " + e_s
    daq_lib.gui_message(message)
    logger.error(message)

  
def openGripper():
  RobotControlLib.openGripper()


def closeGripper():
  RobotControlLib.closeGripper()
  
  
def mountRobotSample(puckPos,pinPos,sampID,init=0,warmup=0):
  global retryMountCount
  global sampXadjust, sampYadjust, sampZadjust  

  absPos = (pinsPerPuck*(puckPos%3))+pinPos+1  
  if (getBlConfig('robot_online')):
    if (not daq_lib.waitGovRobotSE()):
      daq_lib.setGovRobot('SE')
    if (getBlConfig(TOP_VIEW_CHECK) == 1):
      try:
        if (daq_utils.beamline == "fmx"):                  
          _thread.start_new_thread(setWorkposThread,(init,0))        

        sample = db_lib.getSampleByID(sampID)
        sampName = sample['name']
        reqCount = sample['request_count']
        prefix1 = sampName + "_" + str(puckPos) + "_" + str(pinPos) + "_" + str(reqCount) + "_PA_0"
        prefix90 = sampName + "_" + str(puckPos) + "_" + str(pinPos) + "_" + str(reqCount) + "_PA_90"        
        daq_macros.topViewSnap(prefix1,os.getcwd()+"/pinAlign",1,acquire=0)
      except Exception as e:
        e_s = str(e)
        message = "TopView check ERROR, will continue: " + e_s
        daq_lib.gui_message(message)
        logger.error(message)
    logger.info("mounting " + str(puckPos) + " " + str(pinPos) + " " + str(sampID))
    logger.info("absPos = " + str(absPos))
    platePos = int(puckPos/3)
    rotMotTarget = daq_utils.dewarPlateMap[platePos][0]
    rotCP = beamline_lib.motorPosFromDescriptor("dewarRot")
    logger.info("dewar target,CP")
    logger.info("%s %s" % (rotMotTarget,rotCP))
    if (abs(rotMotTarget-rotCP)>1):
      logger.info("rot dewar")
      try:
        if (init == 0):
          RobotControlLib.runCmd("park")
      except Exception as e:
        e_s = str(e)
        message = "ROBOT Park ERROR: " + e_s
        daq_lib.gui_message(message)
        logger.error(message)
        return 0
      beamline_lib.mvaDescriptor("dewarRot",rotMotTarget)
    try:
      if (init):
        setPvDesc("boostSelect",0)
        if (getPvDesc("sampleDetected") == 0): #reverse logic, 0 = true
          setPvDesc("boostSelect",1)
        else:
          robotStatus = beamline_support.get_any_epics_pv("SW:RobotState","VAL")
          if (robotStatus != "Ready"):
            if (daq_utils.beamline == "fmx"):
              daq_macros.homePins()
              time.sleep(3.0)
            if (not daq_lib.setGovRobot('SE')):
              return
        if (getBlConfig(TOP_VIEW_CHECK) == 1):
          omegaCP = beamline_lib.motorPosFromDescriptor("omega")
          if (omegaCP > 89.5 and omegaCP < 90.5):
            beamline_lib.mvrDescriptor("omega", 85.0)
          logger.info("calling thread")                        
          _thread.start_new_thread(wait90TopviewThread,(prefix1,prefix90))
          logger.info("called thread")
        setPvDesc("boostSelect",0)                    
        if (getPvDesc("gripTemp")>-170):
          try:
            RobotControlLib.mount(absPos)
          except Exception as e:
            e_s = str(e)
            message = "ROBOT mount ERROR: " + e_s
            daq_lib.gui_message(message)
            logger.error(message)
            return 0
        else:
          time.sleep(0.5)
          if (getPvDesc("sampleDetected") == 0):
            logger.info("full mount")
            RobotControlLib.mount(absPos)
          else:
            RobotControlLib.initialize()
            RobotControlLib._mount(absPos)
        setPvDesc("boostSelect",1)                                
      else:
        if (getBlConfig(TOP_VIEW_CHECK) == 1):
          omegaCP = beamline_lib.motorPosFromDescriptor("omega")
          if (omegaCP > 89.5 and omegaCP < 90.5):
            beamline_lib.mvrDescriptor("omega", 85.0)
          logger.info("calling thread")            
          _thread.start_new_thread(wait90TopviewThread,(prefix1,prefix90))
          logger.info("called thread")
        if (warmup):
          RobotControlLib._mount(absPos,warmup=True)
        else:
          RobotControlLib._mount(absPos)
      if (getBlConfig(TOP_VIEW_CHECK) == 1):
        daq_lib.setGovRobot('SA')  #make sure we're in SA before moving motors
        if (sampYadjust != 0):
          pass
        else:
          logger.info("Cannot align pin - Mount next sample.")
#else it thinks it worked            return 0
      
      daq_lib.setGovRobot('SA')
      return 1
    except Exception as e:
      logger.error(e)
      e_s = str(e)
      if (e_s.find("Fatal") != -1):
        daq_macros.robotOff()
        daq_macros.disableMount()
        daq_lib.gui_message(e_s + ". FATAL ROBOT ERROR - CALL STAFF! robotOff() executed.")
        return 0                    
      if (e_s.find("tilted") != -1 or e_s.find("Load Sample Failed") != -1):
        if (getBlConfig("queueCollect") == 0):          
          daq_lib.gui_message(e_s + ". Try mounting again")
          return 0            
        else:
          if (retryMountCount == 0):
            retryMountCount+=1
            mountStat = mountRobotSample(puckPos,pinPos,sampID,init)
            if (mountStat == 1):
              retryMountCount = 0
            return mountStat
          else:
            retryMountCount = 0
            daq_lib.gui_message("ROBOT: Could not recover from " + e_s)
            return 2
      daq_lib.gui_message("ROBOT mount ERROR: " + e_s)
      return 0
    return 1
  else:
    return 1

def unmountRobotSample(puckPos,pinPos,sampID): #will somehow know where it came from

  absPos = (pinsPerPuck*(puckPos%3))+pinPos+1  
  robotOnline = getBlConfig('robot_online')
  logger.info("robot online = " + str(robotOnline))
  if (robotOnline):
    detDist = beamline_lib.motorPosFromDescriptor("detectorDist")    
    if (detDist<200.0):
      setPvDesc("govRobotDetDistOut",200.0)
      setPvDesc("govHumanDetDistOut",200.0)          
    daq_lib.setRobotGovState("SE")    
    logger.info("unmounting " + str(puckPos) + " " + str(pinPos) + " " + str(sampID))
    logger.info("absPos = " + str(absPos))
    platePos = int(puckPos/3)
    rotMotTarget = daq_utils.dewarPlateMap[platePos][0]
    rotCP = beamline_lib.motorPosFromDescriptor("dewarRot")
    logger.info("dewar target,CP")
    logger.info("%s %s" % (rotMotTarget,rotCP))
    if (abs(rotMotTarget-rotCP)>1):
      logger.info("rot dewar")
      try:
        RobotControlLib.runCmd("park")
      except Exception as e:
        e_s = str(e)
        message = "ROBOT park ERROR: " + e_s
        daq_lib.gui_message(message)
        logger.error(message)
        return 0
      beamline_lib.mvaDescriptor("dewarRot",rotMotTarget)
    try:
      par_init=(beamline_support.get_any_epics_pv("SW:RobotState","VAL")!="Ready")
      par_cool=(getPvDesc("gripTemp")>-170)
      RobotControlLib.unmount1(init=par_init,cooldown=par_cool)
    except Exception as e:
      e_s = str(e)
      message = "ROBOT unmount ERROR: " + e_s
      daq_lib.gui_message(message)
      logger.error(message)
      return 0
    detDist = beamline_lib.motorPosFromDescriptor("detectorDist")
    if (detDist<200.0):
      beamline_lib.mvaDescriptor("detectorDist",200.0)
    if (beamline_lib.motorPosFromDescriptor("detectorDist") < 199.0):
      logger.error("ERROR - Detector < 200.0!")
      return 0
    try:
      RobotControlLib.unmount2(absPos)
    except Exception as e:
      e_s = str(e)
      if (e_s.find("Fatal") != -1):
        daq_macros.robotOff()
        daq_macros.disableMount()          
        daq_lib.gui_message(e_s + ". FATAL ROBOT ERROR - CALL STAFF! robotOff() executed.")
        return 0
      message = "ROBOT unmount2 ERROR: " + e_s
      daq_lib.gui_message(message)
      logger.error(message)
      return 0
    if (not daq_lib.waitGovRobotSE()):
      daq_lib.clearMountedSample()
      logger.info("could not go to SE")    
      return 0
  return 1



def initStaubliControl():
  global method_pv,var_pv
  method_pv = staubliEpicsLib.MethodPV("SW:startRobotTask")
  var_pv = staubliEpicsLib.MethodPV("SW:setRobotVariable")

def testRobotComm(numTurns=0):
  if (numTurns>0):
    var_pv.execute("nCamDelay",numTurns)
  method_pv.execute("Test",50000)
  logger.info("executing robot task")
  staubliEpicsLib.waitReady()
  logger.info("done executing robot task")

