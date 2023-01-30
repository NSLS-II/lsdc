#!/opt/conda_envs/lsdc-server-2022-3.2/bin/python
import time
import os
import sys
import db_lib
from daq_utils import getBlConfig
import xmltodict
import ispybLib
from config_params import *

baseDirectory = os.environ["PWD"]
directory = sys.argv[1]
cbfDir = directory+"/cbf"
comm_s = "mkdir -p " + cbfDir
os.system(comm_s)
filePrefix = sys.argv[2]
request_id = sys.argv[3]
seqNum = int(sys.argv[4])
beamline = os.environ["BEAMLINE_ID"]
node = getBlConfig("SynchWebSpotNode")
ispybDCID = int(sys.argv[5])

request=db_lib.getRequestByID(request_id)
reqObj = request["request_obj"]
img_width = reqObj["img_width"]
sweep_start = reqObj["sweep_start"]
sweep_end = reqObj["sweep_end"]
range_degrees = abs(sweep_end-sweep_start)  
numimages = round(range_degrees/img_width)
numstart = reqObj["file_number_start"]

for i in range (numstart,numimages,10):
  comm_s = f"ssh -q {node} \"{os.environ['MXPROCESSINGSCRIPTSDIR']}eiger2cbf.sh {request_id} {i} {i} 0 {seqNum}\""
  os.system(comm_s)
# now handle the cbfs with dials
# prerequisite: dials.spot_server running on the host where the processing is to occur, owned by the user who runs LSDC server
comm_s = f"ssh -q {node} \"{os.environ['MXPROCESSINGSCRIPTSDIR']}dials_spotfind.sh {request_id} 0 {seqNum} per_image\""
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
  try:
    ispybLib.insertPlotResult(ispybDCID,i*10,spotTotal,goodBraggCandidates,method2Res,totalIntegratedSignal)
  except Exception as e:
    print(f'exception during insertPlotResult:{e}')
logfile.close()
os.system("rm " + cbfDir + "/*.cbf")









