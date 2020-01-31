#!/usr/bin/python
from __future__ import print_function 

import time
import os
import sys
import shutil

runEdna_version="2020-01-21"

dataFile1 = sys.argv[1]
dataFile2 = sys.argv[2]
transmission = float(sys.argv[3])
flux = float(sys.argv[4])
xbeam_size = float(sys.argv[5])
ybeam_size = float(sys.argv[6])
request_id = sys.argv[7]
beamline = sys.argv[8]

print("runEdna {}".format(runEdna_version))
print("runEdna processing dataFile1:\"{}\", dataFile2:\"{}\", transmission:{}, flux:{}, xbeam_size:{}, ybeam_size:{}, request_id:{}, beamlines:{}".\
format(dataFile1,dataFile2,transmission,flux,xbeam_size,ybeam_size,request_id,beamline))

if ( not os.path.exists( dataFile1 ) ) :
  print("First image file \"{}\" does not exist".format(dataFile1))
  sys.exit()
else:
  if (os.path.exists( "edna_image_0001.cbf" ) ):
    os.remove( "edna_image_0001.cbf" )
  shutil.copy(dataFile1, "edna_image_0001.cbf" )
if ( not os.path.exists( dataFile2 ) ) :
  print("Second image file \"{}\" does not exist".format(dataFile2))
  sys.exit()
else:
  if (os.path.exists( "edna_image_0002.cbf" ) ):
    os.remove( "edna_image_0002.cbf" )
  shutil.copy(dataFile2, "edna_image_0002.cbf" )

if (beamline == "amx"):
  command_string = "/usr/local/crys-local/edna-mx3/mxv1/bin/edna-mxv1-characterisation --verbose --image " + "edna_image_0001.cbf" + " " + "edna_image_0002.cbf" + " --flux " + str(flux) + " --transmission " + str(transmission) + " --minExposureTimePerImage 0.005 --beamSize 0.006"
else:
  command_string = "/usr/local/crys-local/edna-mx3/mxv1/bin/edna-mxv1-characterisation --verbose --image " + "edna_image_0001.cbf" + " " + "edna_image_0002.cbf" + " --flux " + str(flux) + " --transmission " + str(transmission) + " --minExposureTimePerImage 0.01 --beamSize 0.004"
print(command_string)
if ( os.path.exists( "edna.log" ) ) :
  os.remove( "edna.log" )
if ( os.path.exists( "edna.err" ) ) :
  os.remove( "edna.err" )
edna_execution_status = os.system( "%s > edna.log 2> edna.err" % command_string)






