import os
from config_params import BEAM_CHECK
from math import *
import math
import requests
import getpass
import logging
logger = logging.getLogger(__name__)

try:
  import ispybLib
except Exception as e:
  logger.error("daq_utils: ISPYB import error, %s" %e)

import db_lib

global beamline
beamline = os.environ["BEAMLINE_ID"]
global beamlineComm #this is the comm_ioc
beamlineComm = ""
global searchParams
global motor_dict,counter_dict,scan_list,soft_motor_list,pvLookupDict
global detector_id
detector_id = ""
pvLookupDict = {}
motor_dict = {}
counter_dict = {}
scan_list = []
soft_motor_list = []
global screenYCenterPixelsLowMagOffset
screenYCenterPixelsLowMagOffset = 58

EV_ANGSTROM_CONSTANT = 12398.42  # https://www.kmlabs.com/en/wavelength-to-photon-energy-calculator

def getBlConfig(param, beamline=beamline):
        return db_lib.getBeamlineConfigParam(beamline, param)

def setBlConfig(param, value, beamline=beamline):
        db_lib.setBeamlineConfigParam(beamline, param, value)

def init_environment():
  global beamline,detector_id,mono_mot_code,has_beamline,has_xtalview,xtal_url,xtal_url_small,xtalview_user,xtalview_pass,det_type,has_dna,beamstop_x_pvname,beamstop_y_pvname,camera_offset,det_radius,lowMagFOVx,lowMagFOVy,highMagFOVx,highMagFOVy,lowMagPixX,lowMagPixY,highMagPixX,highMagPixY,screenPixX,screenPixY,screenPixCenterX,screenPixCenterY,screenProtocol,screenPhist,screenPhiend,screenWidth,screenDist,screenExptime,screenWave,screenReso,gonioPvPrefix,searchParams,screenEnergy,detectorOffline,imgsrv_host,imgsrv_port,beamlineComm,primaryDewarName,lowMagCamURL,highMagZoomCamURL,lowMagZoomCamURL,highMagCamURL,owner,dewarPlateMap


  owner = getpass.getuser()
  primaryDewarName = getBlConfig("primaryDewarName")
  db_lib.setPrimaryDewarName(primaryDewarName)
  dewarPlateMap = getBlConfig("dewarPlateMap")
  lowMagCamURL = getBlConfig("lowMagCamURL")
  highMagCamURL = getBlConfig("highMagCamURL")
  highMagZoomCamURL = getBlConfig("highMagZoomCamURL")
  lowMagZoomCamURL = getBlConfig("lowMagZoomCamURL")
  lowMagFOVx = float(getBlConfig("lowMagFOVx"))
  lowMagFOVy = float(getBlConfig("lowMagFOVy"))
  highMagFOVx = float(getBlConfig("highMagFOVx")) #digizoom will be this/2
  highMagFOVy = float(getBlConfig("highMagFOVy"))
  lowMagPixX = float(getBlConfig("lowMagPixX")) #for automated images
  lowMagPixY = float(getBlConfig("lowMagPixY"))
  highMagPixX = float(getBlConfig("highMagPixX")) #for automated images
  highMagPixY = float(getBlConfig("highMagPixY"))
  screenPixX = float(getBlConfig("screenPixX"))
  screenPixY = float(getBlConfig("screenPixY"))
  beamlineComm = getBlConfig("beamlineComm")
  screenPixCenterX = screenPixX/2.0
  screenPixCenterY = screenPixY/2.0
  gonioPvPrefix = getBlConfig("gonioPvPrefix")
  detector_id = getBlConfig("detector_id")
  det_radius = getBlConfig("detRadius")
  det_type = getBlConfig("detector_type")
  imgsrv_port = getBlConfig("imgsrv_port")
  imgsrv_host = getBlConfig("imgsrv_host")
  has_dna = int(getBlConfig("has_edna"))
  has_beamline = int(getBlConfig("has_beamline"))
  detectorOffline = int(getBlConfig("detector_offline"))
  has_xtalview = int(getBlConfig("has_xtalview"))
  camera_offset = float(getBlConfig("camera_offset"))
  if (has_xtalview):
    xtal_url_small = getBlConfig("xtal_url_small")
    xtal_url = getBlConfig("xtal_url")
  mono_mot_code = getBlConfig("mono_mot_code")
  screenProtocol = getBlConfig("screen_default_protocol")
  screenDist, screenEnergy, screenExptime, screenPhiend, screenPhist, screenReso, screenTransmissionPercent, screenWidth, screenbeamHeight, screenbeamWidth = getScreenDefaultParams()
  beamstop_x_pvname = getBlConfig("beamstop_x_pvname")
  beamstop_y_pvname = getBlConfig("beamstop_y_pvname")
  varname = "DETECTOR_OFFLINE"
  if varname in os.environ:
    detectorOffline = int(os.environ[varname])
  setBlConfig(BEAM_CHECK,1)


def calc_reso(det_radius,detDistance,wave,theta):

  if (detDistance == 0): #in case distance reads as 0
    distance = 100.0
  else:
    distance = detDistance
  dg2rd = math.pi / 180.0
  theta_radians = float(theta) * dg2rd
  theta_t = (theta_radians + atan(det_radius/float(distance)))/2
  dmin_t = float(wave)/(2*(sin(theta_t)))
  return float("%.2f" % dmin_t)


def distance_from_reso(det_radius,reso,wave,theta):

  try:
    dg2rd = math.pi / 180.0
    theta_radians = float(theta) * dg2rd
    dx = det_radius/(tan(2*(asin(float(wave)/(2*reso)))-theta_radians))
    return float("%.2f" % dx)
  except ValueError:  
    return 501.0 #a safe value for now


def energy2wave(e, digits=2):
  if (float(e)==0.0):
    return 1.0
  else:
    return float(f"%.{digits}f" % (EV_ANGSTROM_CONSTANT/e))

def wave2energy(w, digits=2):
  if (float(w)==0.0):
    return 12600.0
  else:
    return float(f"%.{digits}f" % (EV_ANGSTROM_CONSTANT/w))

def createDefaultRequest(sample_id,createVisit=True):
    """
    Doesn't really create a request, just returns a dictionary
    with the default parameters that can be passed to addRequesttoSample().
    But note that these then get overwritten anyway, and I no longer expose them in screen params dialog
    """

    sample = db_lib.getSampleByID(sample_id)
    try:
      propNum = sample["proposalID"]
    except KeyError:
      propNum = 999999
    if (propNum == None):
      propNum = 999999        
    if (propNum != getProposalID()):
      setProposalID(propNum,createVisit)
    screenDist, screenEnergy, screenExptime, screenPhiend, screenPhist, screenReso, screenTransmissionPercent, screenWidth, screenbeamHeight, screenbeamWidth = getScreenDefaultParams()
    sampleName = str(db_lib.getSampleNamebyID(sample_id))
    basePath = os.getcwd()
    runNum = db_lib.getSampleRequestCount(sample_id)
    (puckPosition,samplePositionInContainer,containerID) = db_lib.getCoordsfromSampleID(beamline,sample_id)          
    request = {"sample": sample_id}
    request["beamline"] = beamline
    requestObj = {
               "sample": sample_id,
               "sweep_start": screenPhist,  "sweep_end": screenPhiend,
               "img_width": screenWidth,
               "exposure_time": screenExptime,
               "protocol": "standard",
               "detDist": screenDist,
               "parentReqID": -1,
               "basePath": basePath,
               "file_prefix": sampleName,
               "directory": basePath+"/" + str(getVisitName()) + "/"+sampleName+"/" + str(runNum) + "/" +db_lib.getContainerNameByID(containerID)+"_"+str(samplePositionInContainer+1)+"/",
               "file_number_start": 1,
               "energy":screenEnergy,
               "wavelength": energy2wave(screenEnergy),
               "resolution": screenReso,
               "slit_height": screenbeamHeight,  "slit_width": screenbeamWidth,
               "attenuation": screenTransmissionPercent,
               "visit_name": getVisitName(),
               "detector": os.environ["DETECTOR_NAME"],
               "beamline": os.environ["BEAMLINE_ID"],
               "pos_x": -999,  "pos_y": 0,  "pos_z": 0,  "pos_type": 'A', "gridStep": 20}
    request["request_obj"] = requestObj

    return request


def getScreenDefaultParams():
    screenPhist = float(getBlConfig( "screen_default_phist"))
    screenPhiend = float(getBlConfig( "screen_default_phi_end"))
    screenWidth = float(getBlConfig( "screen_default_width"))
    screenDist = float(getBlConfig( "screen_default_dist"))
    screenExptime = float(getBlConfig( "screen_default_time"))
    screenReso = float(getBlConfig( "screen_default_reso"))
    screenWave = float(getBlConfig( "screen_default_wave"))
    screenEnergy = float(getBlConfig( "screen_default_energy"))
    screenbeamWidth = float(getBlConfig( "screen_default_beamWidth"))
    screenbeamHeight = float(getBlConfig( "screen_default_beamHeight"))
    screenTransmissionPercent = float(getBlConfig( "stdTrans"))
    return screenDist, screenEnergy, screenExptime, screenPhiend, screenPhist, screenReso, screenTransmissionPercent, screenWidth, screenbeamHeight, screenbeamWidth


def take_crystal_picture(filename=None,czoom=0,reqID=None,omega=-999):
  zoom = int(czoom)
  if not (has_xtalview):
    return
  if (zoom==0):
    r=requests.get(xtal_url)
  else:
    r=requests.get(xtal_url_small)
  data = r.content
  if (filename != None):
    fd = open(filename+".jpg","wb+")
    fd.write(data)
    fd.close()
  if (reqID != None):
    xtalpicJpegDataResult = {}
    imgRef = db_lib.addFile(data)
    xtalpicJpegDataResult["data"] = imgRef
    xtalpicJpegDataResult["omegaPos"] = omega 
    db_lib.addResultforRequest("xtalpicJpeg",reqID,owner=owner,result_obj=xtalpicJpegDataResult,beamline=beamline)



def create_filename(prefix,number):
  if (detector_id == "EIGER-16"):  
   tmp_filename = findOneH5Master(prefix)
  else:
    tmp_filename = "%s_%05d.cbf" % (prefix,int(number))
  if (prefix[0] != "/"):
    cwd = os.getcwd()
    filename = "%s/%s" % (cwd,tmp_filename)
  else:
    filename = tmp_filename
  return filename

def findOneH5Master(prefix):
  comm_s = "ls " + prefix + "*_master.h5 | head -1"
  masterFilename = os.popen(comm_s).read()[0:-1]
  return masterFilename
  

def readPVDesc():
  global beamline_designation,motor_dict,soft_motor_list,scan_list,counter_dict
  
  envname = "EPICS_BEAMLINE_INFO"
  try:
    dbfilename = os.environ[envname]
  except KeyError:
    logger.info(envname + " not defined. Defaulting to epx.db.")
    dbfilename = "epx.db"
  if (os.path.exists(dbfilename) == 0):
    error_msg = "EPICS BEAMLINE INFO %s does not exist.\n Program exiting." % dbfilename
    logger.info(error_msg)
    sys.exit()
  else:
    dbfile = open(dbfilename,'r')
    line = dbfile.readline()
    line = dbfile.readline()
    beamline_designation = line[:-1]
    line = dbfile.readline()
    i = 0
    while(1):
      line = dbfile.readline()
      if (line == ""):
        break
      else:
        line = line[:-1]
        if (line == "#virtual motors"):
          break
        else:
          motor_inf = line.split()
          motor_dict[motor_inf[1]] = beamline_designation +  motor_inf[0]
    while(1):
      line = dbfile.readline()
      if (line == ""):
        break
      else:
        line = line[:-1]
        if (line == "#control PVs"):
          break
        else:
          motor_inf = line.split()
          soft_motor_list.append(beamline_designation + motor_inf[0])
          motor_dict[motor_inf[1]] = beamline_designation + motor_inf[0]          
    while(1):
      line = dbfile.readline()
      if (line == ""):
        break
      else:
        line = line[:-1]
        if (line == "#scanned motors"):
          break
        else:
          inf = line.split()
          pvLookupDict[inf[1]] = beamline_designation + inf[0]          
    while(1):
      line = dbfile.readline()
      if (line == ""):
        break
      else:
        line = line[:-1]
        if (line == "#counters"):
          break
        else:
          scan_list.append(beamline_designation + line + "scanParms")
    line = dbfile.readline()
    counter_inf = line.split()
    counter_dict[counter_inf[1]] = beamline_designation + counter_inf[0]    

def createVisitNameRaw(proposalName, maxNumber=None):
  if maxNumber:
    number = maxNumber + 1
  else:
    number = 1
  return f'mx{proposalName}-{number}', number

def createVisitName(proposalName, maxNumber=None):
  return createVisitNameRaw(proposalName, maxNumber)

def setProposalID(proposalID,createVisit=True):  # TODO JA proposalID implies a database ID, which it is not (just proposal number). Misleading
   if (getProposalID() != proposalID): #proposalID changed - create a new visit.
     logger.info("you changed proposals! " + str(proposalID))
     logger.info('ignoring createVisit for now - ISPyB required to properly account for visit numbers')
     try:
       visitName, visitNum = createVisitName(proposalID)
       db_lib.setBeamlineConfigParam(beamline,"proposal",proposalID)                
     except Exception as e:
       visitName = "999999-1234"
       logger.error("error in set proposal. Error: %s" % e)
     setVisitName(visitName)

def getProposalID():
  return getBlConfig("proposal")

def getVisitName():
  return getBlConfig("visitName")

def setVisitName(visitName):
  return db_lib.setBeamlineConfigParam(beamline,"visitName",visitName)
