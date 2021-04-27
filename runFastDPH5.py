#!/opt/conda_envs/lsdcServer_2020-1.0/bin/python
import os
import sys
import db_lib
from daq_utils import getBlConfig
import xmltodict
import logging
logger = logging.getLogger()
logging.getLogger().setLevel(logging.INFO)
handler1 = logging.FileHandler('fast_dp.txt')
myformat = logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s')
handler1.setFormatter(myformat)
logger.addHandler(handler1)

try:
  import ispybLib
except Exception as e:
  logger.error("runFastDPH5: ISPYB import error, %s" % e)

baseDirectory = os.environ["PWD"]
directory = sys.argv[1]
runningDir = directory+"/fastDPOutput"
comm_s = "mkdir -p " + runningDir
os.system(comm_s)
os.chdir(runningDir) #maybe not needed
numstart = int(float(sys.argv[3]))
request_id = sys.argv[5]
request=db_lib.getRequestByID(request_id) #add another argument false to allow finished requests to be retrieved for testing
owner=request["owner"]
runFastEP = int(sys.argv[6])
node = sys.argv[7]
runDimple = int(sys.argv[8])
dimpleNode = sys.argv[9]
ispybDCID = int(sys.argv[10])

comm_s = f"ssh -q {node} fast_dp.sh {request_id} {numstart}"
logger.info(comm_s)
os.system(comm_s)

fastDPResultFile = runningDir+"/fast_dp.xml"
fd = open(fastDPResultFile)
resultObj = xmltodict.parse(fd.read())
logger.info("finished fast_dp")
logger.info(resultObj)
resultID = db_lib.addResultforRequest("fastDP",request_id,owner,resultObj,beamline=os.environ["BEAMLINE_ID"])
newResult = db_lib.getResult(resultID)
visitName = getBlConfig("visitName")
try:
  ispybLib.insertResult(newResult,"fastDP",request,visitName,ispybDCID,fastDPResultFile)
except Exception as e:
  logger.error("runfastdph5 insert result ispyb error: %s" % e)
if (runFastEP):
  os.system("fast_ep") #looks very bad! running on ca1!
if (runDimple):
  logger.info('run dimple selected')
  sampleID = request["sample"]
  sample = db_lib.getSampleByID(sampleID)
  try:
    modelFilename = sample["model"]
    if (modelFilename == 'nan'):
      modelPDBname = "model.pdb"
    else:
      modelPDBname = modelFilename + ".pdb"
  except KeyError:
      modelPDBname = "model.pdb"    
  dimpleRunningDir = directory+"/dimpleOutput"
  comm_s = "mkdir -p " + dimpleRunningDir
  os.system(comm_s)
  os.chdir(dimpleRunningDir)

  dimpleComm = getBlConfig("dimpleComm")
  comm_s = "ssh  -q " + dimpleNode + " \"cd " + dimpleRunningDir +";" + dimpleComm + " " + runningDir + "/fast_dp.mtz " + baseDirectory + "/" + modelPDBname + " " + dimpleRunningDir + "\""  
  logger.info(comm_s)
  logger.info("running dimple")
  os.system(comm_s)





