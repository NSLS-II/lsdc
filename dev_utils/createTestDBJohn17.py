#!/usr/bin/env python

import time
import db_lib

db_lib.db_connect()
type_name = 'pin'
for i in range (1,25):
  containerName = "XtalPuck1_" + str(i)
  db_lib.createContainer(containerName,16,"johns","16_pin_puck")

for i in range (1,25):
  containerName = "XtalPuck1_" + str(i)
  for j in range (0,16):
    sampleName = "XtalSamp1_"+str(i)+"_"+str(j)
    sampID = db_lib.createSample(sampleName,"johns",kind=type_name)
    db_lib.insertIntoContainer(containerName, "johns",j+1, sampID)
