import sys
import os
import time
from string import *
import daq_utils
import math
from element_info import *
import beamline_support
import daq_lib
import db_lib
import logging
logger = logging.getLogger(__name__)

global scan_detector_count,scan_list,scanfile_root
global CNT
CNT = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

scan_detector_count = 4
global alldone, allstop, scanactive, scanstop

global number_of_counter_readouts
number_of_counter_readouts = 12



def mvrDescriptor(*args): #convenience to get around nasty PV names
  newArgsList = []  
  for i in range(0,len(args),2):
    newArgsList.append(beamline_support.pvNameSuffix_from_descriptor(args[i]))
    newArgsList.append(float(args[i+1]))
  newArgs = tuple(newArgsList)
  mvr(*newArgs)


def mvaDescriptor(*args): #convenience to get around nasty PV names
  newArgsList = []
  if (args[0] == "detectorDist"):
    beamline_support.setPvValFromDescriptor("govRobotDetDist",float(args[1]))
    beamline_support.setPvValFromDescriptor("govHumanDetDist",float(args[1]))
    if (db_lib.getBeamlineConfigParam(daq_utils.beamline,"HePath") == 1):
      return
  
  for i in range(0,len(args),2):
    newArgsList.append(beamline_support.pvNameSuffix_from_descriptor(args[i]))
    newArgsList.append(float(args[i+1]))
  newArgs = tuple(newArgsList)
  mva(*newArgs)


  
def motorPosFromDescriptor(descriptor):
  return get_epics_motor_pos(beamline_support.pvNameSuffix_from_descriptor(descriptor))


def get_epics_motor_pos(motcode): #gets an epics motor pos with error handling
  try:
    current_pos = beamline_support.get_motor_pos(motcode)
    return current_pos
  except KeyError:
    logger.info("No data available for EPICS channel %s\n" % (mcode))
    return -9999.9

def mvr(*args):
    try:
      beamline_support.mvr(*args)
    except KeyboardInterrupt:
      bl_stop_motors()

    
def mva(*args):
    try:    
      beamline_support.mva(*args)
    except Exception as e:      
      bl_stop_motors()
      e_s = str(e)        
      daq_lib.gui_message("detector move error: " + e_s)              
      logger.info(e)

def read_db():
  beamline_support.read_db()

def init_mots():
  global alldone,scanfile_root

  beamline_support.init_motors()
  return

def bl_stop_motors():
  logger.info("stopping motors")  
  stop_motors()
  logger.info("done stopping motors")

def stop_motors():
  beamline_support.stop_motors()
  return


#12/19 - I think most of from here down is not needed, but I'm not fixing what's not broken
# 4/16 - lots of unused stuff from here down. Leave for now until counting and scanning worked out

def datafile(filename):
  beamline_support.datafile(filename)

def newfile(filename_prefix):
  beamline_support.newfile(filename_prefix)

def nowfile():
  return beamline_support.nowfile()

def init_counters():
  beamline_support.init_counters()
  return


def countdwell(time_to_count):
  beamline_support.set_count_time(time_to_count)

def ri():
  global CNT
  local_count = []

  
  local_count = beamline_support.get_counts(beamline_support.get_count_time())  #index0=timer,1=chan2,...
  for i in range(1,number_of_counter_readouts+1):
    CNT[i] = local_count[i-1]   
    update_s = "channel %d: %d" % (i,CNT[i])
    daq_utils.broadcast_output(update_s)
  if (daq_lib.ringfile == "wire"):
    current = daq_utils.ring_current_from_wire(CNT[6],beamline_support.get_count_time())
  else:
    current = daq_utils.ring_current()
  if (beamline_support.get_count_time() > 0 and current > 0):
    daq_lib.set_field("beamline_merit",int((CNT[2]/beamline_support.get_count_time())/current))
  else:
    daq_lib.set_field("beamline_merit",0)


def read_intensity(time_to_count):
  global CNT
  local_count = []
  
  local_count = beamline_support.get_counts(time_to_count)  #index0=timer,1=chan2,...
  for i in range(1,number_of_counter_readouts+1):
    CNT[i] = local_count[i-1]       
    update_s = "channel %d: %d" % (i,CNT[i])
    daq_utils.broadcast_output(update_s)
  if (daq_lib.ringfile == "wire"):
    current = daq_utils.ring_current_from_wire(CNT[6],beamline_support.get_count_time())
  else:
    current = daq_utils.ring_current()
  if (beamline_support.get_count_time() > 0 and current > 0):
    daq_lib.set_field("beamline_merit",int((CNT[2]/beamline_support.get_count_time())/current))
  else:
    daq_lib.set_field("beamline_merit",0)
  

def get_counts(ctime,count_list):
  global CNT

  oldcount = beamline_support.get_count_time()
  CNT = beamline_support.get_counts(ctime)    
  for i in range(len(count_list)):    
    count_list[i] = CNT[i]
  countdwell(oldcount)



def get_scan_points(motcode):
  return beamline_support.get_scan_points(motcode)
  
  
def set_mono_energy_scan_step(stepsize):
  mono_mot_code = beamline_support.get_motor_code(beamline_support.motor_code_from_descriptor("monochromator"))  
  try:
    mono_stepsize_steps = float(stepsize)
    numpoints = beamline_support.get_scan_points(mono_mot_code)
    scan_width = float(mono_stepsize_steps) * float(numpoints-1)
    half_scan_width = scan_width/2.0
    beamline_support.set_scanstart(mono_mot_code,0.0 - half_scan_width)
    beamline_support.set_scanend(mono_mot_code,half_scan_width)
  except ValueError:
    pass


def set_mono_scan_points(numpoints):
  mono_mot_code = beamline_support.get_motor_code(beamline_support.motor_code_from_descriptor("monochromator"))
  step_inc = beamline_support.get_scanstepsize(mono_mot_code)
  scan_width = step_inc * (float(float(numpoints) - 1))
  half_scan_width = scan_width/2.0
  beamline_support.set_scanpoints(mono_mot_code,int(float(numpoints)))
  beamline_support.set_scanstart(mono_mot_code,0.0 - half_scan_width)
  beamline_support.set_scanend(mono_mot_code,half_scan_width)
  
  


#not sure if special mono handling at nsls2
def move_mono(energy):  # for now, not sure if this should go in macros
  mono_mot_code = beamline_support.get_motor_code(beamline_support.motor_code_from_descriptor("monochromator"))
  if (abs(float(get_mono_energy())-float(energy)) > .1):
    mva(mono_mot_code,float(energy))


def get_mono_energy():
  return motorPosFromDescriptor("energy")


def mono_plot_spectrum():
  chooch_file_prefix = specgen("spectrum.dat","",3,2)
  os.system("xmgrace spectrum.spec&")


def monscn():   # for now, not sure if this should go in macros
  mono_mot_code = beamline_support.get_motor_code(beamline_support.motor_code_from_descriptor("monochromator"))  
  beamline_support.newfile("spectrum")
  current_filename = nowfile()
  daq_lib.open_shutter()
  beamline_support.dscan(mono_mot_code)
  daq_lib.close_shutter()    
  command_string = "ln -sf %s spectrum.dat" % current_filename
  os.system(command_string)
  beamline_support.newfile("scandata")      

def specgen(filename,element_edge,transmit_counter,incident_counter):
# skinner 12/10, I'm not using the transmit and incident counter vals, just using 2,3
  now = time.time()
  specdir = "%s/spectra" % os.environ["PWD"]
  if not (os.path.exists(specdir)):
    os.system("mkdir -p " + specdir)    
  current_specname = "%s/spectra/spec%d.spec" % (os.environ["PWD"],now)
  specname = current_specname
  outfile = open(specname,"w+")
  infile = open(filename,"r")
  firstcount = -1
  numlines = 0
  for line in infile.readlines():
    if (line[0] != '#'):
      tokens = split(line)
      stepno = int(tokens[0])
      step_pos = float(tokens[1])
      c2_counts = int(tokens[3])
      c3_counts = int(tokens[4])
      if (firstcount == -1 and c3_counts>0 and c2_counts>0):
        firstcount = float(c3_counts)/float(c2_counts)
      if (c2_counts>0):
        ratio = (float(c3_counts)/float(c2_counts))/firstcount
        outfile.write("%f %f\n" % (step_pos,ratio))
        numlines = numlines + 1
  outfile.close()
  comm_s = "ln -sf %s spectrum.spec" % current_specname
  os.system(comm_s)
  chooch_raw = "%s/spectra/spec%d.raw" % (os.environ["PWD"],now)
  if (daq_lib.beamline == "x25a"):
    os.system("sort -o sorted_chooch.dat  spectrum.spec")
    specname = "sorted_chooch.dat"
  outfile = open(chooch_raw,"w+")
  outfile.write("BNL NSLS %s\n" % element_edge)
  outfile.write("%d\n" % numlines)
  specfile = open(specname,"r")
  for line in specfile.readlines():  
    tokens = split(line)    
    energy = float(tokens[0])
    yaxis = float(tokens[1])
    outfile.write("%f %f\n" % (energy,yaxis))
  outfile.close()
  specfile.close()
  chooch_raw_prefix = chooch_raw[0:len(chooch_raw)-4]
  return chooch_raw_prefix;

    
def guess_element_for_chooch(midpoint_wave_param):
  for line in open("spectrum.dat","r"):
    pass
  tokens = split(line)
  try:
    numpoints = int(tokens[0])
    for line in open("spectrum.dat","r"):
      if (line[0] == "#"):
        continue
      else:
        tokens = split(line)
        if (int(tokens[0]) == (numpoints+2)/2):
          logger.info(line)
          mono_cp_energy = float(tokens[1])
          midpoint_wave = 12398.5/mono_cp_energy
          logger.info(midpoint_wave)
          min_difference = 99.0
          scan_element = "unknown"
          for keyname in list(element_info.keys()):
            if (element_info[keyname][4] == 1 and element_info[keyname][5] == 1):  #it's active, and we test it
              difference = abs(element_info[keyname][3] - midpoint_wave)
              if (difference<min_difference):
                min_difference = difference
                scan_element = keyname
          logger.info("scan_element  = ",scan_element)
          return scan_element
  except ValueError:
    return "Se"
      
  
def spectrum_analysis():
#as of 12/04, this is letting chooch do the analysis

  peak = 0.0
  infl = 0.0
  fprime_peak = 0.0
  fprime_infl = 0.0
  f2prime_peak = 0.0
  f2prime_infl = 0.0
  result_list = [0.0,0.0,0.0,0.0,0.0,0.0,0.0] #expanded on 12/4 to include f', f'', dermin obsolete
  dermin=1.0
  #skinner 12/09 - just get this from energy
  scan_midpoint_w = 12398.5/get_mono_energy()
  scan_element = guess_element_for_chooch(scan_midpoint_w)
  element_edge_info = scan_element + "-" + element_info[scan_element][2]
  chooch_prefix = specgen("spectrum.dat",element_edge_info,3,2)
  if (scan_element != "unknown"):
    comm_s = "chooch -e %s -o %s -p %s %s" % (scan_element,chooch_prefix+".efs",chooch_prefix+".ps",chooch_prefix+".raw")
  else:
    comm_s = "chooch -o %s -p %s %s" % (chooch_prefix+".efs",chooch_prefix+".ps",chooch_prefix+".raw")    
  logger.info(comm_s)
  daq_lib.gui_message("Running Chooch...&")
  for outputline in os.popen(comm_s).readlines():
    logger.info(outputline)
    tokens = split(outputline)    
    if (len(tokens)>4):
      if (tokens[1] == "peak"):
        peak = float(tokens[3])
        fprime_peak = float(tokens[7])
        f2prime_peak = float(tokens[5])        
      elif (tokens[1] == "infl"):
        infl = float(tokens[3])
        fprime_infl = float(tokens[7])
        f2prime_infl = float(tokens[5])        
      else:
        pass
  daq_lib.destroy_gui_message()
  os.system("xmgrace spectrum.spec&")
  os.system("gv.sh "+chooch_prefix+".ps") #kludged with a shell call to get around gv bug
  os.system("ln -sf "+chooch_prefix+".ps latest_chooch_plot.ps")
  result_list[0] = infl
  result_list[1] = peak
  result_list[2] = dermin
  result_list[3] = f2prime_infl
  result_list[4] = fprime_infl  
  result_list[5] = f2prime_peak
  result_list[6] = fprime_peak 
  return result_list


def sp(motcode,posn):
  beamline_support.sp(motcode,posn)
  return


def align(motcode):
  beamline_support.dscan(motcode)
  copy_datafile_to_global(beamline_support.datafile_name,motcode)    
  beamline_support.newfile("scandata")    
  return

def scan(motcode):
  beamline_support.ascan(motcode)
  copy_datafile_to_global(beamline_support.datafile_name,motcode)    
  beamline_support.newfile("scandata")    
  return

def mvf(motcode,counter_num):
  beamline_support.peakScan(motcode,counter_num)
  copy_datafile_to_global(beamline_support.datafile_name,motcode)    
  beamline_support.newfile("scandata")    
  return
      

def po(data_file):
  command_string = "xmgrace -nxy %s&\n" % data_file
  os.system(command_string)


def set_scan_fly(motcode):
  beamline_support.set_scan_fly(motcode)

def set_scan_linear(motcode):
  beamline_support.set_scan_linear(motcode)


def set_scan_relative(motcode):
  beamline_support.set_scan_relative(motcode)
  
def set_scan_absolute(motcode):
  beamline_support.set_scan_absolute(motcode)
  

def set_scanpoints(motcode,numpoints):
  beamline_support.set_scanpoints(motcode,numpoints)


def set_scanstart(motcode,posn):
  beamline_support.set_scanstart(motcode,posn)


def set_scanend(motcode,posn):
  beamline_support.set_scanend(motcode,posn)


def set_scanstepsize(motcode,stepsize):
  beamline_support.set_scanstepsize(motcode,stepsize)

            




