#!/opt/conda_envs/collection-2018-1.0/bin/python
##!/usr/bin/python
import time
import os
import sys
import db_lib
import xmltodict
import daq_utils
import logging
logger = logging.getLogger(__name__)

try:
  import ispybLib
except:
  logger.info("ISPYB import error")

#def generateSpotsFileFromXMLObsolete(fastdpXmlFilename="fast_dp.xml"): #no idea what this is - 6/16

#  tree = ET.parse(fastdpXmlFilename)
#  root = tree.getroot()
#  for i in range (0,len(root)):
#    dataFileName = root[i].find("image").text
#    spots = int(root[i].find("spot_count").text)
#    grid_spots_file.write("%d %s\n" % (spots,dataFileName))
#  grid_spots_file.close()  

baseDirectory = os.environ["PWD"]
directory = sys.argv[1]
cbfDir = directory+"/cbf"
comm_s = "mkdir -p " + cbfDir
os.system(comm_s)
runningDir = directory+"/fastDPOutput"
comm_s = "mkdir -p " + runningDir
os.system(comm_s)
os.chdir(runningDir) #maybe not needed
filePrefix = sys.argv[2]
numstart = int(float(sys.argv[3]))
numimages = int(sys.argv[4])
request_id = sys.argv[5]
request=db_lib.getRequestByID(request_id)
owner=request["owner"]
runFastEP = int(sys.argv[6])
node = sys.argv[7]
runDimple = int(sys.argv[8])
dimpleNode = sys.argv[9]
ispybDCID = int(sys.argv[10])
expectedFilenameList = []
timeoutLimit = 600 #for now
prefix_long = directory+"/"+filePrefix+"_"+str(numstart)
hdfFilepattern = prefix_long+"_master.h5"
CBF_conversion_pattern = cbfDir + "/"+filePrefix + "_"
#comm_s = "ssh  -q " + node + " \"cd " + runningDir +";source /home/jjakoncic/jean_fastdp_prep.sh;fast_dp -j 12 -J 12 -k 60 " + hdfFilepattern  + "\""
fastdpComm = ";source " + os.environ["PROJDIR"] + "wrappers/fastDPWrap2;" + db_lib.getBeamlineConfigParam(os.environ["BEAMLINE_ID"],"fastdpComm")
#fastdpComm = db_lib.getBeamlineConfigParam(os.environ["BEAMLINE_ID"],"fastdpComm")
dimpleComm = db_lib.getBeamlineConfigParam(os.environ["BEAMLINE_ID"],"dimpleComm")  
comm_s = "ssh  -q " + node + " \"cd " + runningDir + fastdpComm + hdfFilepattern  + "\""
#comm_s = "ssh  -q " + node + " \"cd " + runningDir +";source /nfs/skinner/wrappers/fastDPWrap2;fast_dp -j 12 -J 12 -k 60 " + hdfFilepattern  + "\"" 

#comm_s = "ssh  -q " + node + " \"cd " + runningDir +";source /nfs/skinner/wrappers/fastDPWrap;/usr/local/crys-local/fast_dp/bin/fast_dp -J 16 -j 16 -k 70  " + hdfFilepattern  + "\""
logger.info(comm_s)
os.system(comm_s)
fastDPResultFile = runningDir+"/fast_dp.xml"
#fastDPResultFile = "/GPFS/CENTRAL/xf17id2/skinner/ispyb/fast_dp.xml"
#fd = open("fast_dp.xml")
fd = open(fastDPResultFile)
resultObj = xmltodict.parse(fd.read())
logger.info("finished fast_dp")
logger.info(resultObj)
resultID = db_lib.addResultforRequest("fastDP",request_id,owner,resultObj,beamline=os.environ["BEAMLINE_ID"])
newResult = db_lib.getResult(resultID)
visitName = db_lib.getBeamlineConfigParam(os.environ["BEAMLINE_ID"],"visitName")
try:
  ispybLib.insertResult(newResult,"fastDP",request,visitName,ispybDCID,fastDPResultFile)
except:
  logger.info("ispyb error")
if (runFastEP):
  os.system("fast_ep") #looks very bad! running on ca1!
if (runDimple):
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
#  comm_s = "ssh  -q " + node + " \"cd " + runningDir +";source /nfs/skinner/wrappers/fastDPWrap;fast_ep"
#  comm_s = "ssh  -q " + dimpleNode + " \"cd " + dimpleRunningDir +";dimple " + runningDir + "/fast_dp.mtz /GPFS/CENTRAL/xf17id2/jjakoncic/model.pdb " + dimpleRunningDir + "\""
  comm_s = "ssh  -q " + dimpleNode + " \"cd " + dimpleRunningDir +";" + dimpleComm + " " + runningDir + "/fast_dp.mtz " + baseDirectory + "/" + modelPDBname + " " + dimpleRunningDir + "\""  
  logger.info(comm_s)
  logger.info("running dimple")
  os.system(comm_s)





