#!/opt/conda_envs/lsdcServer_2020-1.0/bin/python
import time
import os
import sys
import db_lib
import xmltodict
import ispybLib

baseDirectory = os.environ["PWD"]
directory = sys.argv[1]
cbfDir = directory+"/cbf"
comm_s = "mkdir -p " + cbfDir
os.system(comm_s)
filePrefix = sys.argv[2]
request_id = sys.argv[3]
seqNum = int(sys.argv[4])
beamline = os.environ["BEAMLINE_ID"]
node = db_lib.getBeamlineConfigParam(beamline,"SynchWebSpotNode")
ispybDCID = int(sys.argv[5])

request=db_lib.getRequestByID(request_id)
reqObj = request["request_obj"]
img_width = reqObj["img_width"]
sweep_start = reqObj["sweep_start"]
sweep_end = reqObj["sweep_end"]
range_degrees = abs(sweep_end-sweep_start)  
numimages = round(range_degrees/img_width)
numstart = reqObj["file_number_start"]

cbfComm = db_lib.getBeamlineConfigParam(beamline,"cbfComm")
dialsComm = db_lib.getBeamlineConfigParam(beamline,"dialsComm")
dialsTuneLowRes = db_lib.getBeamlineConfigParam(beamline,"rasterTuneLowRes")
dialsTuneHighRes = db_lib.getBeamlineConfigParam(beamline,"rasterTuneHighRes")
dialsTuneIceRingFlag = db_lib.getBeamlineConfigParam(beamline,"rasterTuneIceRingFlag")
dialsTuneResoFlag = db_lib.getBeamlineConfigParam(beamline,"rasterTuneResoFlag")  
dialsTuneIceRingWidth = db_lib.getBeamlineConfigParam(beamline,"rasterTuneIceRingWidth")
if (dialsTuneIceRingFlag):
  iceRingParams = " ice_rings.filter=true ice_rings.width=" + str(dialsTuneIceRingWidth)
else:
  iceRingParams = ""
if (dialsTuneResoFlag):
  resoParams = " d_min=" + str(dialsTuneLowRes) + " d_max=" + str(dialsTuneHighRes)
else:
  resoParams = ""
dialsCommWithParams = dialsComm + resoParams + iceRingParams
print(dialsCommWithParams)
hdfSampleDataPattern = directory+"/"+filePrefix+"_" 
hdfRowFilepattern = hdfSampleDataPattern + str(int(float(seqNum))) + "_master.h5"
CBF_conversion_pattern = cbfDir + "/" + filePrefix+"_"  
comm_s = "eiger2cbf-linux " + hdfRowFilepattern
for i in range (numstart,numimages,10):
  comm_s = "ssh -q " + node + " \"" + cbfComm + " " + hdfRowFilepattern  + " " + str(i) + ":" + str(i) + " " + CBF_conversion_pattern + ">>/dev/null 2>&1\""   
  os.system(comm_s)
CBFpattern = CBF_conversion_pattern + "*.cbf"

time.sleep(1.0)
comm_s = "ssh -q " + node + " \"ls -rt " + CBFpattern + ">>/dev/null\""
lsOut = os.system(comm_s)
comm_s = "ssh -q " + node + " \"ls -rt " + CBFpattern + "|" + dialsCommWithParams + "\""
print(comm_s)
retry = 3
localDialsResultDict = {}
while(1):
  resultString = "<data>\n"+os.popen(comm_s).read()+"</data>\n"
  localDialsResultDict = xmltodict.parse(resultString)
  if (localDialsResultDict["data"] == None and retry>0):
    print("ERROR \n" + resultString + " retry = " + str(retry))
    retry = retry - 1
    if (retry==0):
      localDialsResultDict["data"]={}
      localDialsResultDict["data"]["response"]=[]
      for jj in range (0,rowCellCount):
        localDialsResultDict["data"]["response"].append({'d_min': '-1.00','d_min_method_1': '-1.00','d_min_method_2': '-1.00','image': '','spot_count': '0','spot_count_no_ice': '0','total_intensity': '0'})
      break
  else:
    break
logfile = open(cbfDir + "/spotLog.txt","a+")  
for i in range (0,len(localDialsResultDict["data"]["response"])):
  spotTotal = localDialsResultDict["data"]["response"][i]['spot_count']
  goodBraggCandidates = localDialsResultDict["data"]["response"][i]['spot_count_no_ice']
  method2Res = localDialsResultDict["data"]["response"][i]['d_min_method_2']
  totalIntegratedSignal = localDialsResultDict["data"]["response"][i]['total_intensity']
  logfile.write(str(i*10) + " " + str(goodBraggCandidates)+"\n")
  ispybLib.insertPlotResult(ispybDCID,i*10,spotTotal,goodBraggCandidates,method2Res,totalIntegratedSignal)
logfile.close()
os.system("rm " + cbfDir + "/*.cbf")









