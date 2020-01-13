#!/usr/bin/env python

import time
import mongoengine

from db_lib import *

type_name = 'pin'
for i in range (1,25):
  containerName = "XtalPuck" + str(i)
  for j in range (0,16):
    sampleName = "XtalSamp_"+str(i)+"_"+str(j)

    try:
      sampID = createSample(sampleName,sample_type=type_name)
    except mongoengine.NotUniqueError:
      raise mongoengine.NotUniqueError('{0}'.format(sampleName))

    insertIntoContainer(containerName, j, sampID)
