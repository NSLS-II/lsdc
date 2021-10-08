import os
import grp
import getpass
import time
import daq_macros
from math import *
from gon_lib import *
from det_lib import *
import robot_lib
import daq_utils
import beamline_lib
import beamline_support
from beamline_support import getPvValFromDescriptor as getPvDesc, setPvValFromDescriptor as setPvDesc
import db_lib
from daq_utils import getBlConfig
from config_params import *
from start_bs import govs
import gov_lib
import logging
logger = logging.getLogger(__name__)

try:
  import ispybLib
except Exception as e:
  logger.error("daq_lib: ISPYB import error, %s" % e)
  
#all keys below are created as beamlineComm PVs. if adding items here, be sure to add them to the simulator
var_list = {'beam_check_flag':0,'overwrite_check_flag':1,'omega':0.00,'kappa':0.00,'phi':0.00,'theta':0.00,'distance':10.00,'rot_dist0':300.0,'inc0':1.00,'exptime0':5.00,'file_prefix0':'lowercase','numstart0':0,'col_start0':0.00,'col_end0':1.00,'scan_axis':'omega','wavelength0':1.1,'datum_omega':0.00,'datum_kappa':0.00,'datum_phi':0.00,'size_mode':0,'spcgrp':1,'state':"Idle",'state_percent':0,'datafilename':'none','active_sweep':-1,'html_logging':1,'take_xtal_pics':0,'px_id':'none','xtal_id':'none','current_pinpos':0,'sweep_count':0,'group_name':'none','mono_energy_target':1.1,'mono_wave_target':1.1,'energy_inflection':12398.5,'energy_peak':12398.5,'wave_inflection':1.0,'wave_peak':1.0,'energy_fall':12398.5,'wave_fall':1.0,'beamline_merit':0,'fprime_peak':0.0,'f2prime_peak':0.0,'fprime_infl':0.0,'f2prime_infl':0.0,'program_state':"Program Ready",'filter':0,'edna_aimed_completeness':0.99,'edna_aimed_ISig':2.0,'edna_aimed_multiplicity':'auto','edna_aimed_resolution':'auto','mono_energy_current':1.1,'mono_energy_scan_step':1,'mono_wave_current':1.1,'mono_scan_points':21,'mounted_pin':(db_lib.beamlineInfo(daq_utils.beamline, 'mountedSample')["sampleID"]),'pause_button_state':'Pause','vector_on':0,'vector_fpp':1,'vector_step':0.0,'vector_translation':0.0,'xia2_on':0,'grid_exptime':0.2,'grid_imwidth':0.2,'choochResultFlag':"0",'xrecRasterFlag':"0"}


global x_vec_start, y_vec_start, z_vec_start, x_vec_end, y_vec_end, z_vec_end, x_vec, y_vec, z_vec
global var_channel_list
global message_string_pv
global gui_popup_message_string_pv
global data_directory_name
global currentIspybDCID

global fastDPNodeCount
fastDPNodeCount = 4
global fastDPNodeCounter
fastDPNodeCounter = 0



global mountCounter
mountCounter = 0

var_channel_list = {}


global abort_flag
abort_flag = 0

def init_var_channels():
  global var_channel_list

  for varname in list(var_list.keys()):
    logger.debug('initing %s' % varname)
    var_channel_list[varname] = beamline_support.pvCreate(daq_utils.beamlineComm + varname)
    if (varname != 'size_mode'):
      beamline_support.pvPut(var_channel_list[varname],var_list[varname])


def gui_message(message_string): 
  beamline_support.pvPut(gui_popup_message_string_pv,message_string)

def destroy_gui_message():
  beamline_support.pvPut(gui_popup_message_string_pv,"killMessage")


def unlatchGov(): # Command needed for FloCos to recover robot
  message1 = f"OLD: unlatchGov called, gov active state = {govs.sel.active.get()}"
  print(message1)
  logger.info(message1)
  govs.sel.active.set(1)
  message2 = f"NEW: unlatchGov called, gov active state = {govs.sel.active.get()}"
  print(message2)
  logger.info(message2)


def set_field(param,val):
  var_list[param] = val
  beamline_support.pvPut(var_channel_list[param],val)


def get_field(param):
  return var_list[param]
    

def set_group_name(group_name):
  set_field("group_name",group_name)

def set_distance_value(distance):
  set_field("distance",atof(distance))
  
def set_xbeam(xbeam): #detector center for image header, in pixels
  setPvDesc("beamCenterX",float(xbeam))

def set_ybeam(ybeam):
  setPvDesc("beamCenterY",float(ybeam))  


def set_beamcenter(xbeam,ybeam): #detector center for image header, in pixels
  set_xbeam(xbeam)
  set_ybeam(ybeam)

def set_space_group(spcgrp):
  set_field("spcgrp",spcgrp)


def beam_monitor_on():
  set_field("beam_check_flag",1)

def beam_monitor_off():
  set_field("beam_check_flag",0)

def overwrite_check_on():
  global allow_overwrite
  
  set_field("overwrite_check_flag",1)
  allow_overwrite = 0

def overwrite_check_off():
  global allow_overwrite  

  set_field("overwrite_check_flag",0)
  allow_overwrite = 1
  
def beam_check_on():
  return get_field("beam_check_flag")


def check_beam():
  return 1

def check_pause():
  global pause_flag

  while (pause_flag==1):
    time.sleep(1.0)

def pause_data_collection():
  global pause_flag

  pause_flag = 1
  set_field("pause_button_state","Continue")
  
def continue_data_collection():
  global pause_flag

  pause_flag = 0
  set_field("pause_button_state","Pause")  


def abort_data_collection(flag):
  global datafile_name,abort_flag,image_started

  if (flag==2): #stop queue after current collection
    abort_flag = 2
    return
  gui_message("Aborting. This may take a minute or more.")  
  while not (getPvDesc("VectorActive")): #only stop if actually collecting
    time.sleep(0.1)
  destroy_gui_message()    
  abort_flag = 1
  time.sleep(1.0)
  gon_stop() #this calls osc abort
  setPvDesc("zebraDisarm",1)
  time.sleep(2)
  detector_stop()


def open_shutter():
  lib_open_shutter()
  set_field("state","Expose")

def close_shutter():
  lib_close_shutter()
  set_field("state","Idle")
  
def init_diffractometer():
  lib_init_diffractometer()

def close_diffractometer():
  lib_close_diffractometer()

def home():
  lib_home()

def home_omega():
  lib_home_omega()


def xtal_id(id):
  set_field("xtal_id",id)


def set_relative_zero(omega,kappa,phi):
  set_field("datum_omega",omega)
  set_field("datum_kappa",kappa)
  set_field("datum_phi",phi)

def relative_zero_to_cp():
  set_field("datum_omega",get_field("omega"))
  set_field("datum_kappa",get_field("kappa"))
  set_field("datum_phi",get_field("phi"))


def unlockGUI():
  logger.info('unlocking GUI')
  beamline_support.set_any_epics_pv(daq_utils.beamlineComm+"zinger_flag","VAL",1)  

def lockGUI():
  logger.info('locking GUI')
  beamline_support.set_any_epics_pv(daq_utils.beamlineComm+"zinger_flag","VAL",-1)  
  
def refreshGuiTree():
  beamline_support.set_any_epics_pv(daq_utils.beamlineComm+"live_q_change_flag","VAL",1)

def broadcast_output(s):
  time.sleep(0.01)
  if (s.find('|') == -1):
    logger.info(s)
  beamline_support.pvPut(message_string_pv,s)


def getRobotConfig():
  return getPvDesc("robotGovConfig",as_string=True)


def setRobotGovState(stateString):
  if (getRobotConfig() == "Robot"):
    setPvDesc("robotGovGo",stateString)
  else:
    setPvDesc("humanGovGo",stateString)

def toggleLowMagCameraSettings(stateCode):

  if (stateCode == "DA"):
    setPvDesc("lowMagGain", getBlConfig(LOW_MAG_GAIN_DA))
    setPvDesc("lowMagAcquireTime",getBlConfig(LOW_MAG_EXP_TIME_DA))
  else:
    setPvDesc("lowMagGain", getBlConfig(LOW_MAG_GAIN))
    setPvDesc("lowMagAcquireTime",getBlConfig(LOW_MAG_EXP_TIME))

def waitGovRobotSE():
  waitGovNoSleep()    
  robotGovState = (getPvDesc("robotSeActive") or getPvDesc("humanSeActive"))
  logger.info("robot gov state = " + str(robotGovState))
  if (robotGovState != 0):
    toggleLowMagCameraSettings("SE")
    return 1
  else:
    logger.info("Governor did not reach SE")
    gui_message("Governor did not reach SE.")    
    return 0

def setGovRobot(state):
  if state == "DI":
    return setGovRobotDI()
  else:
    logger.info('setGovRob%s' % state)
    setRobotGovState(state)
    altName = state.lower().capitalize()
    waitGov()
    robotGovState = (getPvDesc("robot%sActive" % altName) or getPvDesc("human%sActive" % altName))
    logger.info("robot gov state = " + str(robotGovState))
    if (robotGovState != 0):
      if state in ["SA", "DA"]:
        toggleLowMagCameraSettings(state)
      return 1
    else:
      logger.info("Governor did not reach %s" % state)
      gui_message("Governor did not reach %s." % state)
      return 0

def setGovRobot(state):
  try:
    logger.info(f"setGovRobot{state}")
    govStatus = gov_rbt.set(state)
    waitGov(govStatus)
    if state in ["SA", "DA"]:
      toggleLowMagCameraSettings(state)
  except Exception: #TODO verify what kind of exception is thrown if we do not reach state
    logger.info(f"Governor did not reach {state}")


def setGovRobotDI(): # keep this because it is different from the others
  setRobotGovState("DI")
  waitGov()    
  robotGovState = getPvDesc("robotDiActive")
  logger.info("robot gov state = " + str(robotGovState))
  if (robotGovState != 0):
    toggleLowMagCameraSettings("DI")        
    return 1
  else:
    logger.info("Governor did not reach DI")
    gui_message("Governor did not reach DI.")        
    return 0

def govBusy():
  return (getPvDesc("robotGovStatus") == 1 or getPvDesc("humanGovStatus") == 1)

def setGovRobotSA_nowait(): #called at end of a data collection. The idea is this will have time to complete w/o waiting. 
  logger.info("setGovRobotSA")
  toggleLowMagCameraSettings("SA")  
  setRobotGovState("SA")
  return 1

def setGovRobotDI_nowait():
  logger.info("setGovRobotDI")
  toggleLowMagCameraSettings("DI")
  setRobotGovState("DI")
  


def waitGov():
  govTimeout = 120  
  startTime = time.time()
  time.sleep(1.5)  
  while (1):
    robotGovStatus = govBusy()
    logger.info("robot gov status = " + str(robotGovStatus))    
    if (robotGovStatus != 1): #enum 1 = busy
      break
    if (time.time()-startTime > govTimeout):
      logger.info("Governor Timeout!")
      gui_message("Governor Timeout!")          
      return 0
    time.sleep(0.1)        
  time.sleep(1.0)    

def governorWaitCallback():
  logger.info("robot gov status = " + str(robotGovStatus))

def waitGov(status):
  try:
    # TODO add callback for periodic updates
    failure = status.wait(GOVERNOR_TIMEOUT)
    return failure
  except StatusTimeoutError, WaitTimeoutError:
    message = 'Governor Timeout!'
    logger.error(message)
    gui_message(message)

def waitGovNoSleep():
  govTimeout = 120  
  startTime = time.time()
  while (1):
    time.sleep(.05)
    robotGovStatus = govBusy()
    logger.info("robot gov status = " + str(robotGovStatus))    
    if (robotGovStatus != 1): #enum 1 = busy
      break
    if (time.time()-startTime > govTimeout):
      logger.info("Governor Timeout!")
      gui_message("Governor Timeout!")                
      return 0
  
  
def mountSample(sampID):
  global mountCounter

  saveDetDist = beamline_lib.motorPosFromDescriptor("detectorDist")  
  warmUpNeeded = 0
  if (getBlConfig("queueCollect") == 1):
    mountCounter+=1
    if (mountCounter > getBlConfig("robotWarmupInterval")):
      warmUpNeeded = 1
  mountedSampleDict = db_lib.beamlineInfo(daq_utils.beamline, 'mountedSample')
  currentMountedSampleID = mountedSampleDict["sampleID"]
  if (getBlConfig(TOP_VIEW_CHECK) == 1):
    logger.info("setting work pos")
    if (daq_utils.beamline == "amx"):                          
      setPvDesc("robotXWorkPos",getPvDesc("robotXMountPos"))
      setPvDesc("robotYWorkPos",getPvDesc("robotYMountPos"))
      setPvDesc("robotZWorkPos",getPvDesc("robotZMountPos"))
      setPvDesc("robotOmegaWorkPos",90.0)    
      logger.info("done setting work pos")  
  if (currentMountedSampleID != ""): #then unmount what's there
    if (sampID!=currentMountedSampleID):
      puckPos = mountedSampleDict["puckPos"]
      pinPos = mountedSampleDict["pinPos"]
      if (robot_lib.unmountRobotSample(puckPos,pinPos,currentMountedSampleID)):
        db_lib.deleteCompletedRequestsforSample(currentMountedSampleID)
        set_field("mounted_pin","")        
        db_lib.beamlineInfo(daq_utils.beamline, 'mountedSample', info_dict={'puckPos':0,'pinPos':0,'sampleID':""})        
        (puckPos,pinPos,puckID) = db_lib.getCoordsfromSampleID(daq_utils.beamline,sampID)
        if (warmUpNeeded):
          gui_message("Warming gripper. Please stand by.")
          mountCounter = 0
        mountStat = robot_lib.mountRobotSample(puckPos,pinPos,sampID,init=0,warmup=warmUpNeeded)
        if (warmUpNeeded):
          destroy_gui_message()
        if (mountStat == 1):
          set_field("mounted_pin",sampID)
          detDist = beamline_lib.motorPosFromDescriptor("detectorDist")
          if (detDist != saveDetDist):
            if (getBlConfig("HePath") == 0):
              beamline_lib.mvaDescriptor("detectorDist",saveDetDist)
        elif(mountStat == 2):
          return 2
        else:
          return 0
      else:
        return 0
    else: #desired sample is mounted, nothing to do
      return 1
  else: #nothing mounted
    (puckPos,pinPos,puckID) = db_lib.getCoordsfromSampleID(daq_utils.beamline,sampID)
    mountStat = robot_lib.mountRobotSample(puckPos,pinPos,sampID,init=1)
    if (mountStat == 1):
      set_field("mounted_pin",sampID)
    elif(mountStat == 2):
      return 2
    else:
      return 0
  db_lib.beamlineInfo(daq_utils.beamline, 'mountedSample', info_dict={'puckPos':puckPos,'pinPos':pinPos,'sampleID':sampID})
  return 1


def clearMountedSample():
  set_field("mounted_pin","")
  db_lib.beamlineInfo(daq_utils.beamline, 'mountedSample', info_dict={'puckPos':0,'pinPos':0,'sampleID':""})
  

def unmountSample():
  global mountCounter

  logger.info("unmountSample")
  mountCounter = 0
  mountedSampleDict = db_lib.beamlineInfo(daq_utils.beamline, 'mountedSample')
  currentMountedSampleID = mountedSampleDict["sampleID"]
  if (currentMountedSampleID != ""):
    puckPos = mountedSampleDict["puckPos"]
    pinPos = mountedSampleDict["pinPos"]
    if (robot_lib.unmountRobotSample(puckPos,pinPos,currentMountedSampleID)):
      db_lib.deleteCompletedRequestsforSample(currentMountedSampleID)      
      robot_lib.finish()
      set_field("mounted_pin","")
      db_lib.beamlineInfo(daq_utils.beamline, 'mountedSample', info_dict={'puckPos':0,'pinPos':0,'sampleID':""})
      return 1
    else:
      return 0

def unmountCold():
  mountedSampleDict = db_lib.beamlineInfo(daq_utils.beamline, 'mountedSample')
  currentMountedSampleID = mountedSampleDict["sampleID"]
  if (currentMountedSampleID != ""):
    puckPos = mountedSampleDict["puckPos"]
    pinPos = mountedSampleDict["pinPos"]
    if (robot_lib.unmountRobotSample(puckPos,pinPos,currentMountedSampleID)):
      db_lib.deleteCompletedRequestsforSample(currentMountedSampleID)      
      robot_lib.parkGripper()
      set_field("mounted_pin","")
      db_lib.beamlineInfo(daq_utils.beamline, 'mountedSample', info_dict={'puckPos':0,'pinPos':0,'sampleID':""})
      setPvDesc("robotGovActive",1)
      return 1
    else:
      return 0

def waitBeam():
  waiting = 0
  while (1):
    if (getPvDesc("beamAvailable") or getBlConfig("beamCheck") == 0):
      if (waiting):
        waiting = 0
        destroy_gui_message()          
      break
    else:
      if not (waiting):      
        waiting = 1
        gui_message("Waiting for beam. Type beamCheckOff() in lsdcServer window to continue.")
      time.sleep(1.0)

def runDCQueue(): #maybe don't run rasters from here???
  global abort_flag

  autoMounted = 0 #this means the mount was performed from a runQueue, as opposed to a manual mount button push
  logger.info("running queue in daq server")
  while (1):
    if (getBlConfig("queueCollect") == 1 and getBlConfig("beamCheck") == 1):
      waitBeam()
    if (abort_flag):
      abort_flag =  0 #careful about when to reset this
      return
    currentRequest = db_lib.popNextRequest(daq_utils.beamline)
    if (currentRequest == {}):
      break
    logger.info("processing request " + str(time.time()))
    reqObj = currentRequest["request_obj"]
    gov_lib.set_detz_in(reqObj["detDist"])
    if (reqObj["detDist"] >= 200.0 and getBlConfig("HePath") == 0):
      gov_lib.set_detz_out(reqObj["detDist"])
    sampleID = currentRequest["sample"]
    mountedSampleDict = db_lib.beamlineInfo(daq_utils.beamline, 'mountedSample')
    currentMountedSampleID = mountedSampleDict["sampleID"]
    if (currentMountedSampleID != sampleID):
      if (getBlConfig("queueCollect") == 0):
        gui_message("You can only run requests on the currently mounted sample. Remove offending request and continue.")
        return
      mountStat = mountSample(sampleID)
      logger.info("automounting mp= " + currentMountedSampleID + " samp= " + str(sampleID))
      if (mountStat == 1):
        autoMounted = 1
      elif(mountStat == 2):
        db_lib.updatePriority(currentRequest["uid"],-1)
        refreshGuiTree()        
        continue
      else:
        return 0
    db_lib.updatePriority(currentRequest["uid"],99999)
    currentRequest['priority'] = 99999 #TODO have updatePriority return an updated request?
    refreshGuiTree() #just tells the GUI to repopulate the tree from the DB
    logger.info("calling collect data " + str(time.time()))    
    colStatus = collectData(currentRequest)
    logger.info("done collecting data")
    if (autoMounted and db_lib.queueDone(daq_utils.beamline)):
      unmountSample()

    

def stopDCQueue(flag):
  logger.info("stopping queue in daq server " + str(flag))
  abort_data_collection(int(flag))



def logMxRequestParams(currentRequest,wait=True):
  global currentIspybDCID
  reqObj = currentRequest["request_obj"]
  transmissionReadback = getPvDesc("transmissionRBV")
  flux = getPvDesc("flux")
  resultObj = {"requestObj":reqObj,"transmissionReadback":transmissionReadback,"flux":flux}  
  resultID = db_lib.addResultforRequest("mxExpParams",currentRequest["uid"],owner=daq_utils.owner,result_obj=resultObj,proposalID=daq_utils.getProposalID(),beamline=daq_utils.beamline)
  newResult = db_lib.getResult(resultID)
  newResult['result_obj']['requestObj']['xbeam'] = reqObj['xbeam']
  newResult['result_obj']['requestObj']['ybeam'] = reqObj['ybeam']
  db_lib.beamlineInfo(daq_utils.beamline, 'currentSampleID', info_dict={'sampleID':currentRequest["sample"]})
  db_lib.beamlineInfo(daq_utils.beamline, 'currentRequestID', info_dict={'requestID':currentRequest["uid"]})
  logfile = open("dataColLog.txt","a+")
  try:
    logfile.write("\n\ntimestamp: " + time.ctime(currentRequest["time"])+"\n")
  except KeyError:    
    logger.error("caught key error in logging")
    logger.error(currentRequest)
  logfile.write("protocol: " + reqObj["protocol"] +"\n")  
  logfile.write("data prefix: " + reqObj["file_prefix"] +"\n")
  logfile.write("flux: " + str(flux) +"\n")
  logfile.write("transimission percent: " + str(transmissionReadback) +"\n")
  logfile.write("total current (BCU): " + str(getPvDesc("totalCurrentBCU")) +"\n")    
  logfile.write("omega start: " + str(reqObj["sweep_start"]) +"\n")
  logfile.write("omega end: " + str(reqObj["sweep_end"]) +"\n")
  logfile.write("image width: " + str(reqObj["img_width"]) +"\n")
  logfile.write("exposure time per image (s): " + str(reqObj["exposure_time"]) +"\n")
  logfile.write("detector distance: " + str(reqObj["detDist"]) +"\n")
  logfile.write("wavelength: " + str(reqObj["wavelength"]) +"\n")
  logfile.close()
  visitName = daq_utils.getVisitName()
  try: #I'm worried about unforseen ispyb db errors
    #rasters results are entered in ispyb by the GUI, no need to wait
    if wait:
      time.sleep(getBlConfig(ISPYB_RESULT_ENTRY_DELAY))
    currentIspybDCID = ispybLib.insertResult(newResult,"mxExpParams",currentRequest,visitName)
  except Exception as e:
    currentIspybDCID = 999999
    logger.error("logMxRequestParams - ispyb error: %s" % e)



def collectData(currentRequest):
  global data_directory_name,currentIspybDCID,fastDPNodeCount,fastDPNodeCounter

  if (daq_utils.beamline == "fmx"):
    if (getPvDesc("detCoverRBV") == 0):
      logger.info("opening det cover")
      setPvDesc("detCoverOpen",1)
  logMe = 1
  reqObj = currentRequest["request_obj"]
  data_directory_name = str(reqObj["directory"])
  exposure_period = reqObj["exposure_time"]
  wavelength = reqObj["wavelength"]
  resolution = reqObj["resolution"]
  slit_height = reqObj["slit_height"]
  slit_width = reqObj["slit_width"]
  attenuation = reqObj["attenuation"]
  img_width = reqObj["img_width"]
  file_prefix = str(reqObj["file_prefix"])
  logger.info(reqObj["protocol"])
  prot = str(reqObj["protocol"])
  sweep_start = reqObj["sweep_start"]
  sweep_end = reqObj["sweep_end"]
  range_degrees = abs(sweep_end-sweep_start)  
  sweep_start = reqObj["sweep_start"]%360.0
  file_number_start = reqObj["file_number_start"]
  basePath = reqObj["basePath"]
  visitName = daq_utils.getVisitName()
  jpegDirectory = visitName + "/jpegs/" + data_directory_name[data_directory_name.find(visitName)+len(visitName):len(data_directory_name)]  
  colDist = reqObj["detDist"]
    
  status = 1
  if not (os.path.isdir(data_directory_name)):
    logger.debug(f'creating {data_directory_name}')
    comm_s = "mkdir -p " + data_directory_name
    os.system(comm_s)
    comm_s = "chmod 777 " + data_directory_name
    os.system(comm_s)
    comm_s = "mkdir -p " + jpegDirectory
    os.system(comm_s)
    comm_s = "chmod 777 " + jpegDirectory
    os.system(comm_s)
  logger.debug('starting initial motions - transmission and detector distance')
  daq_macros.setTrans(attenuation)
  beamline_lib.mvaDescriptor("detectorDist",colDist)  
  logger.debug('transmission and detector distance done')
  # now that the detector is in the correct position, get the beam center
  currentRequest['request_obj']['xbeam'] = getPvDesc('beamCenterX')
  currentRequest['request_obj']['ybeam'] = getPvDesc('beamCenterY')
  db_lib.updateRequest(currentRequest)
  if (prot == "raster"):
    logger.info('entering raster')
    status = daq_macros.snakeRaster(currentRequest["uid"])
    logger.info('exiting raster')
  elif (prot == "stepRaster"):
    status = daq_macros.snakeStepRaster(currentRequest["uid"])    
  elif (prot == "specRaster"):
    status = daq_macros.snakeStepRasterSpec(currentRequest["uid"])    
  elif (prot == "vector" or prot == "stepVector"):
    imagesAttempted = collect_detector_seq_hw(sweep_start,range_degrees,img_width,exposure_period,file_prefix,data_directory_name,file_number_start,currentRequest)
  elif (prot == "multiCol"):
    daq_macros.snakeRaster(currentRequest["uid"])    
  elif (prot == "rasterScreen"):
    daq_macros.rasterScreen(currentRequest)    
  elif (prot == "multiColQ"):
    daq_macros.multiCol(currentRequest)
  elif (prot == "eScan"):
    daq_macros.eScan(currentRequest)
  else: #standard, screening, or edna - these may require autoalign, checking first
    if (reqObj["pos_x"] != -999):
      beamline_lib.mvaDescriptor("sampleX",reqObj["pos_x"])
      beamline_lib.mvaDescriptor("sampleY",reqObj["pos_y"])
      beamline_lib.mvaDescriptor("sampleZ",reqObj["pos_z"])
    elif (reqObj["centeringOption"] == "Interactive"): #robotic, pause and let user center
      pause_data_collection()
      check_pause()
    else:
      logger.info("autoRaster")
      if not (daq_macros.autoRasterLoop(currentRequest)):
        logger.info("could not center sample")
        db_lib.updatePriority(currentRequest["uid"],-1)
        refreshGuiTree()
        return 0
      else:
        if (reqObj["centeringOption"] == "AutoLoop"):
          reqObj["sweep_start"] = beamline_lib.motorPosFromDescriptor("omega") #%360.0?
          sweep_start = reqObj["sweep_start"]
        if (reqObj["centeringOption"] == "AutoRaster"):
          reqObj["sweep_start"] = beamline_lib.motorPosFromDescriptor("omega") - 90.0 #%360.0?
          sweep_start = reqObj["sweep_start"]
      daq_macros.setTrans(attenuation)      
    if (reqObj["protocol"] == "screen"):
      screenImages = 2
      screenRange = 90
      range_degrees = img_width
      for i in range (0,screenImages):
        sweep_start = reqObj["sweep_start"]+(i*screenRange)
        sweep_end = sweep_start+screenRange
        file_prefix = str(reqObj["file_prefix"]+"_"+str(i*screenRange))
        data_directory_name = str(reqObj["directory"]) # for now
        file_number_start = reqObj["file_number_start"]
        beamline_lib.mvaDescriptor("omega",sweep_start)
        if (i==0):
          imagesAttempted = collect_detector_seq_hw(sweep_start,range_degrees,img_width,exposure_period,file_prefix,data_directory_name,file_number_start,currentRequest,changeState=False)
        else:
          imagesAttempted = collect_detector_seq_hw(sweep_start,range_degrees,img_width,exposure_period,file_prefix,data_directory_name,file_number_start,currentRequest)            
        seqNum = int(detector_get_seqnum())         
        node = getBlConfig("spotNode1")
        comm_s = f'ssh -q {node} \"{os.environ["MXPROCESSINGSCRIPTSDIR"]}eiger2cbf.sh {currentRequest["uid"]} 1 1 sweep_start {seqNum}\"'
        logger.info(comm_s)
        os.system(comm_s)
          
    elif (reqObj["protocol"] == "characterize" or reqObj["protocol"] == "ednaCol"):
      characterizationParams = reqObj["characterizationParams"]
      index_success = daq_macros.dna_execute_collection3(0.0,img_width,2,exposure_period,data_directory_name+"/",file_prefix,1,-89.0,1,currentRequest)
      if (index_success):        
        resultsList = db_lib.getResultsforRequest(currentRequest["uid"]) # because for testing I keep running the same request. Probably not in usual use.
        results = None
        for i in range(0,len(resultsList)):
          if (resultsList[i]['result_type'] == 'characterizationStrategy'):
            results = resultsList[i]
            break
        if (results != None):
          
          strategyResults = results["result_obj"]["strategy"]
          stratStart = strategyResults["start"]
          stratEnd = strategyResults["end"]
          stratWidth = strategyResults["width"]
          stratExptime = strategyResults["exptime"]
          stratTrans = strategyResults["transmission"]          
          stratDetDist = strategyResults["detDist"]
          sampleID = currentRequest["sample"]
          tempnewStratRequest = daq_utils.createDefaultRequest(sampleID)
          newReqObj = tempnewStratRequest["request_obj"]
          newReqObj["sweep_start"] = stratStart
          newReqObj["sweep_end"] = stratEnd
          newReqObj["img_width"] = stratWidth
          newReqObj["exposure_time"] = stratExptime
          newReqObj["attenuation"] = stratTrans
          newReqObj["detDist"] = stratDetDist
          newReqObj["directory"] = data_directory_name
          newReqObj["pos_x"] = beamline_lib.motorPosFromDescriptor("sampleX")
          newReqObj["pos_y"] = beamline_lib.motorPosFromDescriptor("sampleY")
          newReqObj["pos_z"] = beamline_lib.motorPosFromDescriptor("sampleZ")
          newReqObj["fastDP"] = True # this is where you might want a "new from old" request to carry over stuff like this.
          newReqObj["fastEP"] = reqObj["fastEP"]
          newReqObj["dimple"] = reqObj["dimple"]                
          newReqObj["xia2"] = reqObj["xia2"]
          runNum = db_lib.incrementSampleRequestCount(sampleID)
          newReqObj["runNum"] = runNum
          newStratRequest = db_lib.addRequesttoSample(sampleID,newReqObj["protocol"],daq_utils.owner,newReqObj,priority=0,proposalID=daq_utils.getProposalID())
          if (reqObj["protocol"] == "ednaCol"):
            logger.info("new strat req = ")
            logger.info(newStratRequest)
            db_lib.updatePriority(currentRequest["uid"],-1)
            refreshGuiTree()
            collectData(db_lib.getRequestByID(newStratRequest))
            return 1
    else: #standard
      logger.info("moving omega to start " + str(time.time()))      
      beamline_lib.mvaDescriptor("omega",sweep_start)
      imagesAttempted = collect_detector_seq_hw(sweep_start,range_degrees,img_width,exposure_period,file_prefix,data_directory_name,file_number_start,currentRequest)
  try:
    if (logMe) and prot == 'raster':
      logMxRequestParams(currentRequest,wait=False)
    elif (logMe):
      logMxRequestParams(currentRequest)
  except TypeError:
    logger.error("caught type error in logging")
  except IndexError:
    logger.error("caught index error in logging")
  except KeyError as e:
    logger.error('caught key error in logging: %s' % e)
  if (prot == "vector" or prot == "standard" or prot == "stepVector"):
    seqNum = int(detector_get_seqnum())
    comm_s = os.environ["LSDCHOME"] + "/runSpotFinder4syncW.py " + data_directory_name + " " + file_prefix + " " + str(currentRequest["uid"]) + " " + str(seqNum) + " " + str(currentIspybDCID)+ "&"
    logger.info(comm_s)
    os.system(comm_s)    
    if img_width > 0: #no dataset processing in stills mode
      if (reqObj["fastDP"]):
        if (reqObj["fastEP"]):
          fastEPFlag = 1
        else:
          fastEPFlag = 0
        if (reqObj["dimple"]):
          dimpleFlag = 1
        else:
          dimpleFlag = 0        
        nodeName = "fastDPNode" + str((fastDPNodeCounter%fastDPNodeCount)+1)
        fastDPNodeCounter+=1
        node = getBlConfig(nodeName)      
        dimpleNode = getBlConfig("dimpleNode")      
        if (daq_utils.detector_id == "EIGER-16"):
          seqNum = int(detector_get_seqnum())
          comm_s = os.environ["LSDCHOME"] + "/runFastDPH5.py " + data_directory_name + " " + str(seqNum) + " " + str(currentRequest["uid"]) + " " + str(fastEPFlag) + " " + node + " " + str(dimpleFlag) + " " + dimpleNode + " " + str(currentIspybDCID)+ "&"
        else:
          comm_s = os.environ["LSDCHOME"] + "/runFastDP.py " + data_directory_name + " " + file_prefix + " " + str(file_number_start) + " " + str(int(round(range_degrees/img_width))) + " " + str(currentRequest["uid"]) + " " + str(fastEPFlag) + " " + node + " " + str(dimpleFlag) + " " + dimpleNode + "&"
        logger.info(f'Running fastdp command: {comm_s}')
        if (daq_utils.beamline == "amx"):                                            
          visitName = daq_utils.getVisitName()
          if (not os.path.exists(visitName + "/fast_dp_dir")):
            os.system("killall -KILL loop-fdp-dple-populate")
            os.system("cd " + visitName + ";${LSDCHOME}/bin/loop-fdp-dple-populate.sh&")
        os.system(comm_s)
      if (reqObj["xia2"]):
        comm_s = f"ssh -q xf17id2-srv1 \"{os.environ['MXPROCESSINGSCRIPTSDIR']}xia2.sh {currentRequest['uid']} \"&"
        os.system(comm_s)
  
  logger.info('processing should be triggered')
  db_lib.updatePriority(currentRequest["uid"],-1)
  refreshGuiTree()
  logger.info('after refresh GUI tree')
  
  return status

    

def collect_detector_seq_hw(sweep_start,range_degrees,image_width,exposure_period,fileprefix,data_directory_name,file_number,currentRequest,z_target=0,changeState=True): #works for pilatus
  global image_started,allow_overwrite,abort_flag

  logger.info("data directory = " + data_directory_name)
  reqObj = currentRequest["request_obj"]
  protocol = str(reqObj["protocol"])
  sweep_start = sweep_start%360.0
  if (protocol == "vector" or protocol == "stepVector"):
    beamline_lib.mvaDescriptor("omega",sweep_start)
  if (image_width == 0):
    number_of_images = range_degrees
  else:
    number_of_images = round(range_degrees/image_width)
  range_seconds = number_of_images*exposure_period
  if (daq_utils.detector_id == "EIGER-16"):  
    exposure_time = exposure_period - .00001
  else:
    exposure_time = exposure_period - .0024  
  angleStart = sweep_start
  file_prefix_minus_directory = str(fileprefix)
  try:
    file_prefix_minus_directory = file_prefix_minus_directory[file_prefix_minus_directory.rindex("/")+1:len(file_prefix_minus_directory)]
  except ValueError: 
    pass
  logger.info("collect %f degrees for %f seconds %d images exposure_period = %f exposure_time = %f" % (range_degrees,range_seconds,number_of_images,exposure_period,exposure_time))
  if (protocol == "standard" or protocol == "characterize" or protocol == "ednaCol" or protocol == "screen" or protocol == "burn"):
    logger.info("vectorSync " + str(time.time()))    
    daq_macros.vectorSync()
    logger.info("zebraDaq " + str(time.time()))        
    RE(daq_macros.zebraDaq(angleStart,range_degrees,image_width,exposure_period,file_prefix_minus_directory,data_directory_name,file_number,3,changeState))
#    daq_macros.zebraDaq(angleStart,range_degrees,image_width,exposure_period,file_prefix_minus_directory,data_directory_name,file_number,3,protocol=protocol)  #?protocol?
  elif (protocol == "vector"):
    daq_macros.vectorZebraScan(currentRequest)  
  elif (protocol == "stepVector"):
    daq_macros.vectorZebraStepScan(currentRequest)
  else:
    pass
  return 


def detectorArm(angle_start,image_width,number_of_images,exposure_period,fileprefix,data_directory_name,file_number): #will need some environ info to diff eiger/pilatus
  global image_started,allow_overwrite,abort_flag

  detector_save_files()
  detector_set_username(getpass.getuser())
  detector_set_groupname(grp.getgrgid(os.getgid())[0])
  detector_set_fileperms(420)
  logger.info("data directory = " + data_directory_name)

  file_prefix_minus_directory = str(fileprefix)
  try:
    file_prefix_minus_directory = file_prefix_minus_directory[file_prefix_minus_directory.rindex("/")+1:len(file_prefix_minus_directory)]
  except ValueError: 
    pass
  detector_set_exposure_time(exposure_period)  
  detector_set_period(exposure_period) #apparently this takes care of itself for deadtime
  detector_set_numimages(number_of_images)
  detector_set_filepath(data_directory_name)
  detector_set_fileprefix(file_prefix_minus_directory)
  detector_set_filenumber(file_number)
  detector_set_fileheader(angle_start,image_width,beamline_lib.motorPosFromDescriptor("detectorDist"),beamline_lib.motorPosFromDescriptor("wavelength"),0.0,exposure_period,getPvDesc("beamCenterX"),getPvDesc("beamCenterY"),"omega",angle_start,0.0,0.0) #only a few for eiger
  
  detector_start() #but you need wired or manual trigger
  startArm = time.time()
  detector_waitArmed() #don't worry about this while we're not doing hardware triggers., not quite sure what it means
  endArm = time.time()
  armTime = endArm-startArm
  logger.info("\narm time = " + str(armTime) +"\n")
  return

def checkC2C_X(x,fovx): # this is to make sure the user doesn't make too much of an x-move in C2C
  scalePixX = getPvDesc("image_X_scalePix")
  centerPixX = getPvDesc("image_Y_centerPix")
  xpos = beamline_lib.motorPosFromDescriptor("sampleX")
  target = xpos + ((x-centerPixX) * (fovx/scalePixX))
  logger.info('checkC2C_X target: %s' % target)
  xlimLow = getPvDesc("robotXMountPos") + getPvDesc("robotXMountLowLim")
  xlimHi = getPvDesc("robotXMountPos") + getPvDesc("robotXMountHiLim")
  if (target<xlimLow or target>xlimHi):
    gui_message("Click to Center out of bounds on X move. Please mount next sample.")
    return 0
  return 1
  

def center_on_click(x,y,fovx,fovy,source="screen",maglevel=0,jog=0): #maglevel=0 means lowmag, high fov, #1 = himag with digizoom option, 
  #source=screen = from screen click, otherwise from macro with full pixel dimensions
  if (getBlConfig('robot_online')): #so that we don't move things when robot moving?
    robotGovState = (getPvDesc("robotSaActive") or getPvDesc("humanSaActive"))
    if (not robotGovState):
      return
    if not (checkC2C_X(x,fovx)):
      return
  if (source == "screen"):
    waitGovNoSleep()
    setPvDesc("image_X_scalePix",daq_utils.screenPixX) #these are video dimensions in the gui
    setPvDesc("image_Y_scalePix",daq_utils.screenPixY)
    setPvDesc("image_X_centerPix",daq_utils.screenPixX/2)
    setPvDesc("image_Y_centerPix",daq_utils.screenPixY/2)
    setPvDesc("image_X_scaleMM",float(fovx))
    setPvDesc("image_Y_scaleMM",float(fovy))
    
  else:
    if (int(maglevel)==0): #I think hardcoded to not use maglevel anymore, replaced with more flexible fov
      setPvDesc("image_X_scalePix",daq_utils.lowMagPixX)
      setPvDesc("image_Y_scalePix",daq_utils.lowMagPixY)
      setPvDesc("image_X_centerPix",daq_utils.lowMagPixX/2)
      setPvDesc("image_Y_centerPix",daq_utils.lowMagPixY/2)
      setPvDesc("image_X_scaleMM",float(fovx))
      setPvDesc("image_Y_scaleMM",float(fovy))
      
    else:
      setPvDesc("image_X_scalePix",daq_utils.lowMagPixX)
      setPvDesc("image_Y_scalePix",daq_utils.lowMagPixY)
      setPvDesc("image_X_centerPix",daq_utils.highMagPixX/2)
      setPvDesc("image_Y_centerPix",daq_utils.highMagPixY/2)
      setPvDesc("image_X_scaleMM",float(fovx))
      setPvDesc("image_Y_scaleMM",float(fovy))

  omega_mod = beamline_lib.motorPosFromDescriptor("omega")%360.0
  lib_gon_center_xtal(x,y,omega_mod,0)
  if (jog):
    beamline_lib.mvrDescriptor("omega",float(jog))


def setProposalID(proposalID):
  daq_utils.setProposalID(proposalID)

def getProposalID():
  return daq_utils.getProposalID()


