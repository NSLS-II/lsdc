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
import sys
import traceback
import _thread
import logging
import epics.ca
import top_view

from config_params import TOP_VIEW_CHECK, DETECTOR_SAFE_DISTANCE, MOUNT_SUCCESSFUL, MOUNT_FAILURE,\
                          MOUNT_UNRECOVERABLE_ERROR
logger = logging.getLogger(__name__)

global pinsPerPuck
pinsPerPuck = 16

global sampXadjust, sampYadjust, sampZadjust
sampXadjust = 0
sampYadjust = 0
sampZadjust = 0

global retryMountCount
retryMountCount = 0

class EMBLRobot:
    def finish():
      if (getBlConfig('robot_online')):
        try:
          RobotControlLib.runCmd("finish")
          return MOUNT_SUCCESSFUL
        except Exception as e:
          e_s = str(e)
          message = "ROBOT Finish ERROR: " + e_s
          daq_lib.gui_message(message)
          logger.error(message)
          return MOUNT_FAILURE

    def warmupGripperRecoverThread(savedThreshold,junk):
      time.sleep(120.0)
      setPvDesc("warmupThreshold",savedThreshold)


    def recoverRobot():
      try:
        rebootEMBL()
        time.sleep(8.0)
        _,bLoaded,_ = RobotControlLib.recover()
        if bLoaded:
          daq_macros.robotOff()
          daq_macros.disableMount()
          daq_lib.gui_message("Found a sample in the gripper - CALL STAFF! disableMount() executed.")
        else:
          RobotControlLib.runCmd("goHome")
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
      try:
        RobotControlLib.rebootEMBL()
      except Exception as e:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_type == epics.ca.ChannelAccessGetFailure and str(exc_value) == "Get failed; status code: 192":
          logger.info('channel access failure detected but error 192 is expected, so continuing')
        else:
          # channel access exception with error 192 seems "normal". only raise for other exceptions
          logger.error('rebootEMBL exception: %s' % traceback.format_exception(exc_type, exc_value, exc_tb))
          raise(e)


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


    # pin alignment, then dewar alignment done here
    def preMount(puckPos, pinPos, sampID, **kwargs):
      init = kwargs.get("init", 0)
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
            top_view.topViewSnap(prefix1,os.getcwd()+"/pinAlign",1,acquire=0)
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
            return MOUNT_FAILURE
          beamline_lib.mvaDescriptor("dewarRot",rotMotTarget)


    def callAlignPinThread(prefix1, prefix90):
            if (getBlConfig(TOP_VIEW_CHECK) == 1):
              omegaCP = beamline_lib.motorPosFromDescriptor("omega")
              if (omegaCP > 89.5 and omegaCP < 90.5):
                beamline_lib.mvrDescriptor("omega", 85.0)
              logger.info("calling thread")
              _thread.start_new_thread(top_view.wait90TopviewThread,(prefix1,prefix90))
              logger.info("called thread")


    def mount(puckPos,pinPos,sampID,**kwargs):
      global retryMountCount
      global sampXadjust, sampYadjust, sampZadjust

      init = kwargs.get("init", 0)
      warmup = kwargs.get("warmup", 0)
      absPos = (pinsPerPuck*(puckPos%3))+pinPos+1
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
                  return MOUNT_FAILURE
            callAlignPinThread(prefix1, prefix90)
            setPvDesc("boostSelect",0)
            if (getPvDesc("gripTemp")>-170):
              try:
                RobotControlLib.mount(absPos)
              except Exception as e:
                e_s = str(e)
                message = "ROBOT mount ERROR: " + e_s
                daq_lib.gui_message(message)
                logger.error(message)
                return MOUNT_FAILURE
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
            callAlignPinThread(prefix1, prefix90)
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
          return MOUNT_SUCCESSFUL
        except Exception as e:
          logger.error(e)
          e_s = str(e)
          if (e_s.find("Fatal") != -1):
            daq_macros.robotOff()
            daq_macros.disableMount()
            daq_lib.gui_message(e_s + ". FATAL ROBOT ERROR - CALL STAFF! robotOff() executed.")
            return MOUNT_FAILURE
          if (e_s.find("tilted") != -1 or e_s.find("Load Sample Failed") != -1):
            if (getBlConfig("queueCollect") == 0):
              daq_lib.gui_message(e_s + ". Try mounting again")
              return MOUNT_FAILURE
            else:
              if (retryMountCount == 0):
                retryMountCount+=1
                mountStat = mountRobotSample(puckPos,pinPos,sampID,init=init)
                if (mountStat == 1):
                  retryMountCount = 0
                return mountStat
              else:
                retryMountCount = 0
                daq_lib.gui_message("ROBOT: Could not recover from " + e_s)
                return MOUNT_UNRECOVERABLE_ERROR
          daq_lib.gui_message("ROBOT mount ERROR: " + e_s)
          return MOUNT_FAILURE
        return MOUNT_SUCCESSFUL
      else:
        return MOUNT_SUCCESSFUL


    def postMount(puck, pinPos, sampID):
      global sampYadjust
      global workposThread
      if (getBlConfig(TOP_VIEW_CHECK) == 1):
        if daq_utils.beamline == "fmx":
          try: #make sure workposThread is finished before proceeding to robotGovActive check
            timeout = 20
            start_time = time.time()
            while workposThread.isAlive():
              time.sleep(0.5)
              if time.time() - start_time > timeout:
                raise Exception(f'setWorkposThread failed to finish before {timeout}s timeout')
            logger.info(f'Time waiting for workposThread: {time.time() - start_time}s')
          except Exception as e:
            daq_lib.gui_message(e)
            logger.error(e)
            return MOUNT_FAILURE
          if getPvDesc('robotGovActive') == 0: #HACK, if FMX and top view, if stuck in robot inactive
                                           #(due to setWorkposThread),
            logger.info('FMX, top view active, and robot stuck in inactive - restoring to active')
            setPvDesc('robotGovActive', 1) #set it active
          else:
            logger.info('not changing anything as governor is active')
        if (sampYadjust == 0):
          logger.info("Cannot align pin - Mount next sample.")
      daq_lib.setGovRobot('SA')
      return MOUNT_SUCCESSFUL

 
    def preUnmount(puckPos,pinPos,sampID): #will somehow know where it came from
      absPos = (pinsPerPuck*(puckPos%3))+pinPos+1
      robotOnline = getBlConfig('robot_online')
      logger.info("robot online = " + str(robotOnline))
      if (robotOnline):
        detDist = beamline_lib.motorPosFromDescriptor("detectorDist")
        if (detDist<DETECTOR_SAFE_DISTANCE):
          setPvDesc("govRobotDetDistOut",DETECTOR_SAFE_DISTANCE)
          setPvDesc("govHumanDetDistOut",DETECTOR_SAFE_DISTANCE)
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
            return MOUNT_FAILURE
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
          return MOUNT_FAILURE
        detDist = beamline_lib.motorPosFromDescriptor("detectorDist")
        if (detDist<DETECTOR_SAFE_DISTANCE):
          beamline_lib.mvaDescriptor("detectorDist",DETECTOR_SAFE_DISTANCE)
        if (beamline_lib.motorPosFromDescriptor("detectorDist") < (DETECTOR_SAFE_DISTANCE - 1.0)):
          logger.error(f"ERROR - Detector < {DETECTOR_SAFE_DISTANCE}")
          return MOUNT_FAILURE
        return MOUNT_SUCCESSFUL

    def unmount(puckPos, pinPos, sampID, absPos):
        try:
          RobotControlLib.unmount2(absPos)
        except Exception as e:
          e_s = str(e)
          if (e_s.find("Fatal") != -1):
            daq_macros.robotOff()
            daq_macros.disableMount()
            daq_lib.gui_message(e_s + ". FATAL ROBOT ERROR - CALL STAFF! robotOff() executed.")
            return MOUNT_FAILURE
          message = "ROBOT unmount2 ERROR: " + e_s
          daq_lib.gui_message(message)
          logger.error(message)
          return MOUNT_FAILURE
        if (not daq_lib.waitGovRobotSE()):
          daq_lib.clearMountedSample()
          logger.info("could not go to SE")
          return MOUNT_FAILURE
        return MOUNT_SUCCESSFUL
