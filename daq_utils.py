import time
import os
from math import *
import requests
import xmltodict
import getpass
import logging
logger = logging.getLogger(__name__)

try:
  import ispybLib
except:
  logger.info("ISPYB import error")

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

def init_environment():
  global beamline,detector_id,mono_mot_code,has_beamline,has_xtalview,xtal_url,xtal_url_small,xtalview_user,xtalview_pass,det_type,has_dna,beamstop_x_pvname,beamstop_y_pvname,camera_offset,det_radius,lowMagFOVx,lowMagFOVy,highMagFOVx,highMagFOVy,lowMagPixX,lowMagPixY,highMagPixX,highMagPixY,screenPixX,screenPixY,screenPixCenterX,screenPixCenterY,screenProtocol,screenPhist,screenPhiend,screenWidth,screenDist,screenExptime,screenWave,screenReso,gonioPvPrefix,searchParams,screenEnergy,detectorOffline,imgsrv_host,imgsrv_port,beamlineComm,primaryDewarName,lowMagCamURL,highMagZoomCamURL,lowMagZoomCamURL,highMagCamURL,owner,dewarPlateMap


  owner = getpass.getuser()
  primaryDewarName = db_lib.getBeamlineConfigParam(beamline,"primaryDewarName")
  db_lib.setPrimaryDewarName(primaryDewarName)
  dewarPlateMap = db_lib.getBeamlineConfigParam(beamline,"dewarPlateMap")
  lowMagCamURL = db_lib.getBeamlineConfigParam(beamline,"lowMagCamURL")
  highMagCamURL = db_lib.getBeamlineConfigParam(beamline,"highMagCamURL")
  highMagZoomCamURL = db_lib.getBeamlineConfigParam(beamline,"highMagZoomCamURL")
  lowMagZoomCamURL = db_lib.getBeamlineConfigParam(beamline,"lowMagZoomCamURL")
  lowMagFOVx = float(db_lib.getBeamlineConfigParam(beamline,"lowMagFOVx"))
  lowMagFOVy = float(db_lib.getBeamlineConfigParam(beamline,"lowMagFOVy"))
  highMagFOVx = float(db_lib.getBeamlineConfigParam(beamline,"highMagFOVx")) #digizoom will be this/2
  highMagFOVy = float(db_lib.getBeamlineConfigParam(beamline,"highMagFOVy"))
  lowMagPixX = float(db_lib.getBeamlineConfigParam(beamline,"lowMagPixX")) #for automated images
  lowMagPixY = float(db_lib.getBeamlineConfigParam(beamline,"lowMagPixY"))
  highMagPixX = float(db_lib.getBeamlineConfigParam(beamline,"highMagPixX")) #for automated images
  highMagPixY = float(db_lib.getBeamlineConfigParam(beamline,"highMagPixY"))
  screenPixX = float(db_lib.getBeamlineConfigParam(beamline,"screenPixX"))
  screenPixY = float(db_lib.getBeamlineConfigParam(beamline,"screenPixY"))
  beamlineComm = db_lib.getBeamlineConfigParam(beamline,"beamlineComm")
  screenPixCenterX = screenPixX/2.0
  screenPixCenterY = screenPixY/2.0
  gonioPvPrefix = db_lib.getBeamlineConfigParam(beamline,"gonioPvPrefix")
  detector_id = db_lib.getBeamlineConfigParam(beamline,"detector_id")
  det_radius = db_lib.getBeamlineConfigParam(beamline,"detRadius")
  det_type = db_lib.getBeamlineConfigParam(beamline,"detector_type")
  imgsrv_port = db_lib.getBeamlineConfigParam(beamline,"imgsrv_port")
  imgsrv_host = db_lib.getBeamlineConfigParam(beamline,"imgsrv_host")
  has_dna = int(db_lib.getBeamlineConfigParam(beamline,"has_edna"))
  has_beamline = int(db_lib.getBeamlineConfigParam(beamline,"has_beamline"))
  detectorOffline = int(db_lib.getBeamlineConfigParam(beamline,"detector_offline"))
  has_xtalview = int(db_lib.getBeamlineConfigParam(beamline,"has_xtalview"))
  camera_offset = float(db_lib.getBeamlineConfigParam(beamline,"camera_offset"))
  if (has_xtalview):
    xtal_url_small = db_lib.getBeamlineConfigParam(beamline,"xtal_url_small")
    xtal_url = db_lib.getBeamlineConfigParam(beamline,"xtal_url")
  mono_mot_code = db_lib.getBeamlineConfigParam(beamline,"mono_mot_code")
  screenProtocol = db_lib.getBeamlineConfigParam(beamline,"screen_default_protocol")
  screenPhist = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_phist"))
  screenPhiend = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_phi_end"))
  screenWidth = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_width"))
  screenDist =  float(db_lib.getBeamlineConfigParam(beamline,"screen_default_dist"))
  screenExptime = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_time"))
  screenReso = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_reso"))
  screenWave = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_wave"))
  screenEnergy = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_energy"))
  screenbeamWidth = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_beamWidth"))
  screenbeamHeight = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_beamHeight"))
  screenTransmissionPercent = float(db_lib.getBeamlineConfigParam(beamline,"stdTrans"))
  beamstop_x_pvname = db_lib.getBeamlineConfigParam(beamline,"beamstop_x_pvname")
  beamstop_y_pvname = db_lib.getBeamlineConfigParam(beamline,"beamstop_y_pvname")
  varname = "DETECTOR_OFFLINE"
  if varname in os.environ:
    detectorOffline = int(os.environ[varname])



def calc_reso(det_radius,detDistance,wave,theta):

  if (detDistance == 0): #in case distance reads as 0
    distance = 100.0
  else:
    distance = detDistance
  dg2rd = 3.14159265 / 180.0
  theta_radians = float(theta) * dg2rd
  theta_t = (theta_radians + atan(det_radius/float(distance)))/2
  dmin_t = float(wave)/(2*(sin(theta_t)))
  return float("%.2f" % dmin_t)


def distance_from_reso(det_radius,reso,wave,theta):

  try:
    dg2rd = 3.14159265 / 180.0
    theta_radians = float(theta) * dg2rd
    dx = det_radius/(tan(2*(asin(float(wave)/(2*reso)))-theta_radians))
    return float("%.2f" % dx)
  except ValueError:  
    return 501.0 #a safe value for now


def energy2wave(e):
  if (float(e)==0.0):
    return 1.0
  else:
    return float("%.2f" % (12398.5/e))

def wave2energy(w):
  if (float(w)==0.0):
    return 12600.0
  else:
    return float("%.2f" % (12398.5/w))

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
    screenPhist = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_phist"))
    screenPhiend = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_phi_end"))
    screenWidth = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_width"))
    screenDist =  float(db_lib.getBeamlineConfigParam(beamline,"screen_default_dist"))
    screenExptime = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_time"))
    screenReso = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_reso"))
    screenWave = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_wave"))
    screenEnergy = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_energy"))
    screenbeamWidth = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_beamWidth"))
    screenbeamHeight = float(db_lib.getBeamlineConfigParam(beamline,"screen_default_beamHeight"))
    screenTransmissionPercent = float(db_lib.getBeamlineConfigParam(beamline,"stdTrans"))
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
               "pos_x": -999,  "pos_y": 0,  "pos_z": 0,  "pos_type": 'A', "gridStep": 20}
    request["request_obj"] = requestObj

    return request



def take_crystal_picture(filename=None,czoom=0,reqID=None,omega=-999):
  zoom = int(czoom)
  if not (has_xtalview):
    return
  if (1):
    if (zoom==0):
      r=requests.get(xtal_url)
    else:
      r=requests.get(xtal_url_small)
  else: #password, need to change to requests module if we need this
    comm_s = "curl -u %s:%s -o %s.jpg -s %s" % (xtalview_user,xtalview_pass,filename,xtal_url)
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
   tmp_filename = findH5Master(prefix)
  else:
    tmp_filename = "%s_%05d.cbf" % (prefix,int(number))
  if (prefix[0] != "/"):
    cwd = os.getcwd()
    filename = "%s/%s" % (cwd,tmp_filename)
  else:
    filename = tmp_filename
  return filename

def findH5Master(prefix):
  comm_s = "ls " + prefix + "*_master.h5"
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


def setProposalID(proposalID,createVisit=True):
  if (getProposalID() != proposalID): #proposalID changed - create a new visit.
    logger.info("you changed proposals! " + str(proposalID))
    try:
      if (createVisit):
        visitName = ispybLib.createVisit(proposalID)
        db_lib.setBeamlineConfigParam(beamline,"proposal",proposalID)                
      else:
        visitName = ispybLib.createVisitName(proposalID)
    except:
      visitName = "999999-1234"
      logger.info("ispyb error in set proposal")
    setVisitName(visitName)

def getProposalID():
  return db_lib.getBeamlineConfigParam(beamline,"proposal")

def getVisitName():
  return db_lib.getBeamlineConfigParam(beamline,"visitName")

def setVisitName(visitName):
  return db_lib.setBeamlineConfigParam(beamline,"visitName",visitName)

