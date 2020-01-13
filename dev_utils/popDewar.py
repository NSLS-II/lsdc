#!/usr/bin/python

from db_lib import *

primary_dewar_name = "primaryDewar2"

createContainer(primary_dewar_name, "dewar", 24) 

for i in range (1,21):
  containerName = "Puck" + str(i)
  insertIntoContainer(primary_dewar_name, i, getContainerIDbyName(containerName))
