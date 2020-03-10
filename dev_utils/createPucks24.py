#!/usr/bin/python

from db_lib import *

for i in range (1,25):
  containerName = "XtalPuck" + str(i)
  createContainer(containerName,"16_pin_puck")
