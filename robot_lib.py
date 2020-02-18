#this will evolve for the staubli. Will need to know currently mounted sample. Will need to store this in the db.
#import staubliEpicsLib
#import stateModule

import RobotControlLib
import daq_utils
import db_lib
import daq_lib
import beamline_lib
import time
import daq_macros
import beamline_support
import os
import filecmp
import _thread
import logging
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
  if (db_lib.getBeamlineConfigParam(daq_utils.beamline,'robot_online')):  
    try:
      RobotControlLib.runCmd("finish")
      return 1    
    except Exception as e:
      e_s = str(e)        
      daq_lib.gui_message("ROBOT Finish ERROR: " + e_s)        
      logger.info(e)
#      daq_lib.gui_message(e)
      return 0

def warmupGripperRecoverThread(savedThreshold,junk):
  time.sleep(120.0)
  beamline_support.setPvValFromDescriptor("warmupThreshold",savedThreshold)      

def wait90TopviewThread(prefix1,prefix90):
  global sampXadjust, sampYadjust, sampZadjust

  sampXadjust = 0
  sampYadjust = 0
  sampZadjust = 0
  startTime = time.time()
  if (beamline_support.getPvValFromDescriptor("gripTemp")>-170):
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
      beamline_support.setPvValFromDescriptor("topViewTrigMode",0)    
      beamline_support.setPvValFromDescriptor("topViewImMode",2)
      beamline_support.setPvValFromDescriptor("topViewDataType",1)
      beamline_support.setPvValFromDescriptor("topViewAcquire",1,wait=False)    
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
        xlimLow = beamline_support.getPvValFromDescriptor("robotXMountPos") + beamline_support.getPvValFromDescriptor("robotXMountLowLim")
        xlimHi = beamline_support.getPvValFromDescriptor("robotXMountPos") + beamline_support.getPvValFromDescriptor("robotXMountHiLim")
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
          beamline_support.setPvValFromDescriptor("robotXWorkPos",sampXAbsolute)
          beamline_support.setPvValFromDescriptor("robotYWorkPos",sampYAbsolute)
          beamline_support.setPvValFromDescriptor("robotZWorkPos",sampZAbsolute)          
      else:
        logger.info("Cannot align pin - Mount next sample.")
#else it thinks it worked            return 0
      for outputline in lines:
        logger.info(outputline)
  except Exception as e:
    e_s = str(e)        
    daq_lib.gui_message("TopView check ERROR, will continue: " + e_s)        
    logger.info(e_s)
    
  
  
def recoverRobot():
  try:
    rebootEMBL()
    time.sleep(8.0)    
    RobotControlLib.runCmd("recover")
#    saveThreshold = beamline_support.getPvValFromDescriptor("warmupThresholdRBV")
#    beamline_support.setPvValFromDescriptor("warmupThreshold",50)
#    _thread.start_new_thread(warmupGripperRecoverThread,(saveThreshold,0))
#    warmupGripper()
  except Exception as e:
    e_s = str(e)
    daq_lib.gui_message("ROBOT Recover failed! " + e_s)            


def dryGripper():
  try:
    saveThreshold = beamline_support.getPvValFromDescriptor("warmupThresholdRBV")
    beamline_support.setPvValFromDescriptor("warmupThreshold",50)
    _thread.start_new_thread(warmupGripperRecoverThread,(saveThreshold,0))
    warmupGripperForDry()
  except Exception as e:
    e_s = str(e)
    daq_lib.gui_message("Dry gripper failed! " + e_s)
    beamline_support.setPvValFromDescriptor("warmupThreshold",saveThreshold)          
    
def DewarAutoFillOn():
  RobotControlLib.runCmd("turnOnAutoFill")
  enableDewarTscreen()

def DewarAutoFillOff():
  RobotControlLib.runCmd("turnOffAutoFill")
  enableDewarTscreen()

def DewarHeaterOn():
  RobotControlLib.runCmd("dewarHeaterOn")
  enableDewarTscreen()
  
def DewarHeaterOff():
  RobotControlLib.runCmd("dewarHeaterOff")
  enableDewarTscreen()


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
  enableDewarTscreen()

def closePorts():
  RobotControlLib.runCmd("closePorts")
  enableDewarTscreen()
  
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
    daq_lib.gui_message("Park gripper Failed!: " + e_s)        
    logger.info(e_s)
    

def setWorkposThread(init,junk):
  logger.info("setting work pos in thread")
  beamline_support.setPvValFromDescriptor("robotGovActive",1)
  beamline_support.setPvValFromDescriptor("robotXWorkPos",beamline_support.getPvValFromDescriptor("robotXMountPos"))
  beamline_support.setPvValFromDescriptor("robotYWorkPos",beamline_support.getPvValFromDescriptor("robotYMountPos"))
  beamline_support.setPvValFromDescriptor("robotZWorkPos",beamline_support.getPvValFromDescriptor("robotZMountPos"))
  beamline_support.setPvValFromDescriptor("robotOmegaWorkPos",90.0)
  if (init):
    time.sleep(20)
    beamline_support.setPvValFromDescriptor("robotGovActive",0)      

def testRobot():
  try:
    RobotControlLib.testRobot()
    logger.info("Test Robot passed!")
    daq_lib.gui_message("Test Robot passed!")
  except Exception as e:
    e_s = str(e)        
    daq_lib.gui_message("Test Robot failed!: " + e_s)        
    logger.info(e_s)

  
def openGripper():
  RobotControlLib.openGripper()


def closeGripper():
  RobotControlLib.closeGripper()
  
  
def mountRobotSample(puckPos,pinPos,sampID,init=0,warmup=0):
  global retryMountCount
  global sampXadjust, sampYadjust, sampZadjust  

#  absPos = (pinsPerPuck*puckPos)+pinPos+1
  absPos = (pinsPerPuck*(puckPos%3))+pinPos+1  
  if (db_lib.getBeamlineConfigParam(daq_utils.beamline,'robot_online')):
    if (not daq_lib.waitGovRobotSE()):
      daq_lib.setGovRobotSE()
    if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"topViewCheck") == 1):
      try:
        if (daq_utils.beamline == "fmx"):                  
          _thread.start_new_thread(setWorkposThread,(init,0))        
#        logger.info("setting work pos")
#        beamline_support.setPvValFromDescriptor("robotGovActive",1)
#        beamline_support.setPvValFromDescriptor("robotXWorkPos",beamline_support.getPvValFromDescriptor("robotXMountPos"))
#        beamline_support.setPvValFromDescriptor("robotYWorkPos",beamline_support.getPvValFromDescriptor("robotYMountPos"))
#        beamline_support.setPvValFromDescriptor("robotZWorkPos",beamline_support.getPvValFromDescriptor("robotZMountPos"))
#        beamline_support.setPvValFromDescriptor("robotGovActive",0)      

        sample = db_lib.getSampleByID(sampID)
        sampName = sample['name']
        reqCount = sample['request_count']
        prefix1 = sampName + "_" + str(puckPos) + "_" + str(pinPos) + "_" + str(reqCount) + "_PA_0"
        prefix90 = sampName + "_" + str(puckPos) + "_" + str(pinPos) + "_" + str(reqCount) + "_PA_90"        
        daq_macros.topViewSnap(prefix1,os.getcwd()+"/pinAlign",1,acquire=0)
      except Exception as e:
        e_s = str(e)        
        daq_lib.gui_message("TopView check ERROR, will continue: " + e_s)        
        logger.info(e_s)
    logger.info("mounting " + str(puckPos) + " " + str(pinPos) + " " + str(sampID))
    logger.info("absPos = " + str(absPos))
    platePos = int(puckPos/3)
    rotMotTarget = daq_utils.dewarPlateMap[platePos][0]
    rotCP = beamline_lib.motorPosFromDescriptor("dewarRot")
    logger.info("dewar target,CP")
    logger.info(rotMotTarget,rotCP)
    if (abs(rotMotTarget-rotCP)>1):
      logger.info("rot dewar")
      try:
        if (init == 0):
          RobotControlLib.runCmd("park")
      except Exception as e:
        e_s = str(e)        
        daq_lib.gui_message("ROBOT Park ERROR: " + e_s)                  
        logger.info(e)
        return 0
      beamline_lib.mvaDescriptor("dewarRot",rotMotTarget)
    try:
      if (init):
        beamline_support.setPvValFromDescriptor("boostSelect",0)
        if (beamline_support.getPvValFromDescriptor("sampleDetected") == 0): #reverse logic, 0 = true
          beamline_support.setPvValFromDescriptor("boostSelect",1)
        else:
#            if (beamline_support.getPvValFromDescriptor("gripTemp") > 20.0): #gripper warm
          robotStatus = beamline_support.get_any_epics_pv("SW:RobotState","VAL")
          if (robotStatus != "Ready"):
            if (daq_utils.beamline == "fmx"):
              daq_macros.homePins()
              time.sleep(3.0)
            if (not daq_lib.setGovRobotSE()):
              return
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"topViewCheck") == 1):
          omegaCP = beamline_lib.motorPosFromDescriptor("omega")
          if (omegaCP > 89.5 and omegaCP < 90.5):
            beamline_lib.mvrDescriptor("omega", 85.0)
          logger.info("calling thread")                        
          _thread.start_new_thread(wait90TopviewThread,(prefix1,prefix90))
          logger.info("called thread")
        beamline_support.setPvValFromDescriptor("boostSelect",0)                    
        if (beamline_support.getPvValFromDescriptor("gripTemp")>-170):
          try:
            RobotControlLib.mount(absPos)
          except Exception as e:
            e_s = str(e)        
            daq_lib.gui_message("ROBOT mount ERROR: " + e_s)        
            logger.info(e)
            return 0
        else:
          time.sleep(0.5)
          if (beamline_support.getPvValFromDescriptor("sampleDetected") == 0):
            logger.info("full mount")
            RobotControlLib.mount(absPos)
          else:
            RobotControlLib.initialize()
            RobotControlLib._mount(absPos)
        beamline_support.setPvValFromDescriptor("boostSelect",1)                                
      else:
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"topViewCheck") == 1):
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
      if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"topViewCheck") == 1):
        daq_lib.setGovRobotSA()  #make sure we're in SA before moving motors
        if (sampYadjust != 0):
          pass
#          logger.info("move samp x,y,z (nm) " + str(sampXadjust) + " " + str(sampYadjust) + " "+ str(sampZadjust))
#          beamline_lib.mvrDescriptor("sampleX",sampXadjust)
#          beamline_lib.mvrDescriptor("sampleY",sampYadjust)
#          beamline_lib.mvrDescriptor("sampleZ",sampZadjust)
        else:
          logger.info("Cannot align pin - Mount next sample.")
#else it thinks it worked            return 0
      
      daq_lib.setGovRobotSA()
      return 1
    except Exception as e:
      logger.info(e)
      e_s = str(e)
#      if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"topViewCheck") == 1):      
#        beamline_lib.mvrDescriptor("omega", 90.0) #this will allow topview camera thread to terminate gracefully      
      if (e_s.find("Fatal") != -1):
        daq_macros.robotOff()
        daq_macros.disableMount()
        daq_lib.gui_message(e_s + ". FATAL ROBOT ERROR - CALL STAFF! robotOff() executed.")
        return 0                    
      if (e_s.find("tilted") != -1 or e_s.find("Load Sample Failed") != -1):
        if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"queueCollect") == 0):          
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

#  absPos = (pinsPerPuck*puckPos)+pinPos+1
  absPos = (pinsPerPuck*(puckPos%3))+pinPos+1  
  robotOnline = db_lib.getBeamlineConfigParam(daq_utils.beamline,'robot_online')
  logger.info("robot online = " + str(robotOnline))
  if (robotOnline):
    detDist = beamline_lib.motorPosFromDescriptor("detectorDist")    
    if (detDist<200.0):
      beamline_support.setPvValFromDescriptor("govRobotDetDistOut",200.0)
      beamline_support.setPvValFromDescriptor("govHumanDetDistOut",200.0)          
    daq_lib.setRobotGovState("SE")    
    logger.info("unmounting " + str(puckPos) + " " + str(pinPos) + " " + str(sampID))
    logger.info("absPos = " + str(absPos))
    platePos = int(puckPos/3)
    rotMotTarget = daq_utils.dewarPlateMap[platePos][0]
    rotCP = beamline_lib.motorPosFromDescriptor("dewarRot")
    logger.info("dewar target,CP")
    logger.info(rotMotTarget,rotCP)
    if (abs(rotMotTarget-rotCP)>1):
      logger.info("rot dewar")
      try:
        RobotControlLib.runCmd("park")
      except Exception as e:
        e_s = str(e)        
        daq_lib.gui_message("ROBOT park ERROR: " + e_s)        
        logger.info(e)
        return 0
      beamline_lib.mvaDescriptor("dewarRot",rotMotTarget)
    try:
      par_init=(beamline_support.get_any_epics_pv("SW:RobotState","VAL")!="Ready")
      par_cool=(beamline_support.getPvValFromDescriptor("gripTemp")>-170)
#      if par_cool == False and daq_utils.beamline == "fmx": 
#        time.sleep(3)
      RobotControlLib.unmount1(init=par_init,cooldown=par_cool)
    except Exception as e:
      e_s = str(e)        
      daq_lib.gui_message("ROBOT unmount ERROR: " + e_s)        
      logger.info(e)
      return 0
    detDist = beamline_lib.motorPosFromDescriptor("detectorDist")
    if (detDist<200.0):
      beamline_lib.mvaDescriptor("detectorDist",200.0)
    if (beamline_lib.motorPosFromDescriptor("detectorDist") < 199.0):
      logger.info("ERROR - Detector < 200.0!")
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
      daq_lib.gui_message("ROBOT unmount2 ERROR: " + e_s)        
      logger.info(e)
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

