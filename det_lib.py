import sys
import os
import time
from string import *
import epics_det

#detector routines

#pixel array specific start

def detector_set_username(username):
  epics_det.det_set_username(username)

def detector_save_files():
  epics_det.det_save_files()

def detector_set_groupname(groupname):
  epics_det.det_set_groupname(groupname)
  
def detector_set_fileperms(fileperms):
  epics_det.det_set_fileperms(fileperms)


def detector_set_period(period):
  print("set detector period " + str(period))
  epics_det.det_set_image_period(period)

def detector_set_exposure_time(exptime):
  print("set detector exposure time " + str(exptime))
  epics_det.det_set_exptime(exptime)

def detector_get_seqnum():
  return epics_det.det_getSeqNum()

def detector_get_deadtime():
  return epics_det.det_get_deadtime()

def detector_setImagesPerFile(numimages):
  epics_det.det_setImagesPerFile(numimages)

def detector_set_numimages(numimages):
  print("set detector number of images " + str(numimages))
  epics_det.det_set_numimages(numimages)

def detector_set_filepath(filepath):
  print("set detector file path " + filepath)
  epics_det.det_set_filepath(filepath)

def detector_set_fileprefix(fileprefix):
  print("set detector file prefix " + fileprefix)
  epics_det.det_set_fileprefix(fileprefix)

#def detector_set_fileNamePattern(fileNamePattern):
#  print "set detector file name pattern " + fileNamePattern
#  epics_det.det_set_fileprefix(fileprefix)

def detector_set_filenumber(filenumber): #I think this does nothing with the eiger
  print("set detector file number " + str(filenumber))
  epics_det.det_set_filenum(filenumber)

def detector_wait():
  epics_det.det_wait()

def detector_waitArmed():
  epics_det.det_waitArmed()
#pixel array specific end

def init_detector():
  print("init detector")
  epics_det.det_channels_init()
  epics_det.det_set_numexposures(1)

def detector_start():
  print("start detector")  
  epics_det.det_start()

def detector_trigger():
  print("trigger detector")  
  epics_det.det_trigger()

def get_trigger_mode():
  return epics_det.det_get_trigger_mode()

def detector_stop_acquire():
  epics_det.det_stop_acquire()
  
def detector_set_trigger_mode(mode):
  epics_det.det_set_trigger_mode(mode)

def detector_set_trigger_exposure(expTime):
  epics_det.det_set_trigger_exposure(expTime)

def detector_set_num_triggers(numTrigs):
  epics_det.det_set_num_triggers(numTrigs)
  
def detector_is_manual_trigger():
  return epics_det.det_is_manual_trigger()
  
def detector_stop():
  print("stop detector")  
  epics_det.det_stop()  
  
def detector_write(flag):
#  adsc_write(int(flag))
  pass

def detector_bin():
  epics_det.det_set_bin(2)

def detector_unbin():
  epics_det.det_set_bin(1)  

def detector_collect_darks(exptime):
  pass

def detector_set_filename(filename):
  print("detector filename")
  print(filename)
  last_slash = rfind(filename,"/")
  last_underscore = rfind(filename,"_")
  last_dot = rfind(filename,".")
  img_path = filename[0:last_slash]
  epics_det.det_set_filepath(img_path)
  img_prefix = filename[last_slash+1:last_underscore]
  epics_det.det_set_fileprefix(img_prefix)
  img_number = filename[last_underscore+1:last_dot]
  epics_det.det_set_filenum(int(img_number))

def detector_set_fileheader(phist,phiinc,dist,wave,theta,exptime,xbeam,ybeam,rot_ax,o,k,p):
#bogus rot axis,
  print("detector filehead")  
  epics_det.det_setheader(float(phist),float(phiinc),float(dist),float(wave),
                 float(theta),float(exptime),float(xbeam),float(ybeam),
                 0,float(o),float(k),float(p))


def detector_set_filekind(flag):
  pass

#  if (flag == 1):
#    adsc_setfilekind(4)
#  else:
#    adsc_setfilekind(5)





