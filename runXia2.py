#!/usr/bin/python
import time
import os
import sys
import db_lib
import json
import daq_utils


directory = sys.argv[1]
runningDir = directory+"/xia2Output"
comm_s = "mkdir -p " + runningDir
os.system(comm_s)
os.chdir(runningDir)

filePrefix = sys.argv[2]
numstart = int(sys.argv[3])
numimages = int(sys.argv[4])
request_id = int(sys.argv[5])

expectedFilenameList = []
timeoutLimit = 60 #for now
prefix_long = directory+"/"+filePrefix
for i in range (numstart,numstart+numimages):
  filename = daq_utils.create_filename(prefix_long,i)
  expectedFilenameList.append(filename)
timeout_check = 0
while(not os.path.exists(expectedFilenameList[len(expectedFilenameList)-1])): #this waits for images
  timeout_check = timeout_check + 1
  time.sleep(1.0)
  if (timeout_check > timeoutLimit):
    break
comm_s = "xia2 " + directory
print(comm_s)
os.system(comm_s)
fd = open("xia2.json")
resultObj = json.loads(fd.read())
fd.close()
print(resultObj)
db_lib.addResultforRequest("xia2",request_id,resultObj)
print("finished xia2")





