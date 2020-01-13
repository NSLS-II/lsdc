#!/usr/bin/python

from db_lib import *
import time

for i in range (1,25):
  containerName = "XtalPuck" + str(i)
  createContainer(containerName,"16_pin_puck")
