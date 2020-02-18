#!/opt/conda_envs/collection-2018-1.0/bin/ipython -i
##!/opt/conda_envs/lsdc_dev3/bin/ipython -i
###!/usr/bin/python -Wignore
#from __future__ import (absolute_import, division, print_function,unicode_literals)
import string
import sys
import os
import time
import _thread
import db_lib
import daq_macros
from daq_macros import *
import daq_lib
from daq_lib import *
import daq_utils
from robot_lib import *
import det_lib
import beamline_support
import beamline_lib
from beamline_lib import *
#import stateModule
import atexit

import logging
from logging import handlers
logger = logging.getLogger()
logging.getLogger().setLevel(logging.INFO)
handler1 = handlers.RotatingFileHandler('lsdcServerLog.txt', maxBytes=50000000)
handler2 = handlers.RotatingFileHandler('/var/log/dama/%slsdcServerLog.txt' % os.environ['BEAMLINE_ID'], maxBytes=50000000)
myformat = logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s')
handler1.setFormatter(myformat)
handler2.setFormatter(myformat)
logger.addHandler(handler1)
logger.addHandler(handler2)

sitefilename = ""
global command_list,immediate_command_list,z
command_list = []
immediate_command_list = []
z = 25

  
def execute_command(command_s):
###  from daq_macros import * #this is so macros can be reloaded on-the-fly
#  refresh_screen(0,0)  
  exec(command_s)


def pybass_init():
  global message_string_pv

  daq_utils.init_environment()
  init_var_channels()
  det_lib.init_detector()  
  daq_lib.message_string_pv = beamline_support.pvCreate(daq_utils.beamlineComm + "message_string")    
  daq_lib.gui_popup_message_string_pv = beamline_support.pvCreate(daq_utils.beamlineComm + "gui_popup_message_string")    
  if (1):
#  if (daq_lib.has_beamline): # for now
    beamline_lib.read_db()
    logger.info("init mots")
#      beamline_support.init_motors()
    init_mots()    #for now
    logger.info("init done mots")
    init_diffractometer()
  try:
    sitefilename = os.environ["LSDC_SITE_FILE"]
  except KeyError:
    gui_message("\$LSDC_SITE_FILE not defined. Questionable defaults in effect.")
  if (sitefilename != ""):    
    if (os.path.exists(sitefilename) == 0):
      error_msg = "\$LSDC_SITE_FILE: %s does not exist. Questionable defaults in effect." % sitefilename
      gui_message(error_msg)
    else:
      process_command_file(sitefilename)


def process_command_file(command_file_name):
  echo_s =  "reading %s\n" % command_file_name
  logger.info(echo_s)
  command_file = open(command_file_name,"r")  
  while 1:
    command = command_file.readline()
    if not command:
      break
    else:
      input_tokens = string.split(command)
      if (len(input_tokens)>0):
        command_string = "%s(" % input_tokens[0]
        for i in range(1,len(input_tokens)):
          command_string = command_string + "\"" + input_tokens[i] + "\""
          if (i != (len(input_tokens)-1)):
            command_string = command_string + ","
        command_string = command_string + ")"
      logger.info(command_string)
      try:
        exec(command_string);    
      except NameError:
        error_string = "Unknown command: " + command_string
        logger.info(error_string)
      except SyntaxError:
        logger.info("Syntax error")
      except KeyError:
        logger.info("Key error")
#  refresh_screen(1,0)
  command_file.close()
  


def process_immediate_commands(frequency):
#  global immediate_command_list
  while (1):
    if (len(immediate_command_list) > 0):
      process_input(immediate_command_list.pop(0))
#      daq_utils.broadcast_output("Command> ")            
##      logger.info "Command> "
    time.sleep(frequency)      

def process_commands(frequency):
  while (1):
    if (len(command_list) > 0):
      process_input(command_list.pop(0))
#      daq_utils.broadcast_output("Command> ")            
##      logger.info "Command> "
######    time.sleep(frequency)
    plt.pause(frequency)    

    
def print_status_thread(frequency):
  global count_list,ring_intensity

  previous_image_started = 0
  percent_done = 0
  shutter_dead_time = .6
  while 1:
    time.sleep(frequency)
    current_percent_done = daq_lib.get_field("state_percent")
    if (daq_lib.image_started > 0):
      if (start_time == 0 or daq_lib.image_started != previous_image_started):
        previous_image_started = daq_lib.image_started
        start_time = time.time()
      now = time.time()
      total_time = float(daq_lib.image_started)
      if (total_time>0.0):
        percent_done = int(.5+((now-start_time)/total_time*100))
      else:
        percent_done = 0
    else:
      start_time = 0
      percent_done = 0
    if (percent_done != current_percent_done):
      daq_lib.set_field("state_percent",percent_done)


def comm_cb(value=None, char_value=None, **kw):
  command = char_value
  command_list.append(command)
  
def comm2_cb(value=None, char_value=None, **kw):
  command = char_value
  if not (command == "\n"):
    immediate_command_list.append(command)
  


def process_input(command_string):
  if (command_string == ""):
    return
#    daq_utils.broadcast_output(time.ctime(time.time()))
  if (command_string == "q"):
    sys.exit()
  daq_lib.broadcast_output(time.ctime(time.time()) + "\n" + command_string)      
  try:
    daq_lib.set_field("program_state","Program Busy")
    execute_command(command_string)
  except NameError:
    error_string = "Unknown command: " + command_string
    logger.info(error_string)
  except SyntaxError:
    logger.info("Syntax error")
  except KeyError:
    logger.info("Key error")
  except TypeError:
    logger.info("Type error")
  except AttributeError:
    logger.info("Attribute Error")
  except KeyboardInterrupt:
    abort_data_collection()
    logger.info("Interrupt caught by daq server\n")
  if (command_string != "pause_data_collection()" and command_string != "continue_data_collection()" and command_string != "abort_data_collection()" and command_string != "unmount_after_abort()" and command_string != "no_unmount_after_abort()"):
    daq_lib.set_field("program_state","Program Ready")


def run_server():
#  _thread.start_new_thread(process_commands,(.05,))  
  _thread.start_new_thread(process_immediate_commands,(.25,))  
  comm_pv = beamline_support.pvCreate(daq_utils.beamlineComm + "command_s")
  beamline_support.pvPut(comm_pv,"\n")
  immediate_comm_pv = beamline_support.pvCreate(daq_utils.beamlineComm + "immediate_command_s")
  beamline_support.pvPut(immediate_comm_pv,"\n")  
  comm_pv.add_callback(comm_cb)
  immediate_comm_pv.add_callback(comm2_cb)
  process_commands(0.5)  

#@atexit.register
#def goodbye():
#  comm_s = "killall -KILL daq_main2.py"
#  os.system(comm_s)

def main(mode):
  pybass_init()
  if (mode=="gui"):
    run_server()
  else:
    lsdcHome = os.environ["LSDCHOME"]
    os.system(lsdcHome+"/daq_main2.py gui&")    

if (len(sys.argv)>1):
  if (sys.argv[1] == "gui"):
    main(mode="gui")
else:
  main(mode="shell")  
