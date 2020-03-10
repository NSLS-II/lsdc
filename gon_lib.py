import time
import beamline_lib
import beamline_support
import logging
logger = logging.getLogger(__name__)


def backlightBrighter():
  intensity=beamline_support.getPvValFromDescriptor("backLightVal")
  intensity = intensity+5  
  beamline_support.setPvValFromDescriptor("backLightVal",intensity)  

def backlightDimmer():
  intensity=beamline_support.getPvValFromDescriptor("backLightVal")
  intensity = intensity-5
  beamline_support.setPvValFromDescriptor("backLightVal",intensity)  

def lib_init_diffractometer():
  beamline_support.initControlPVs()


def lib_gon_center_xtal(x,y,angle_omega,angle_phi):
  beamline_support.setPvValFromDescriptor("C2C_TargetX",float(x))
  beamline_support.setPvValFromDescriptor("C2C_TargetY",float(y))
  beamline_support.setPvValFromDescriptor("C2C_Omega",angle_omega)  
  beamline_support.setPvValFromDescriptor("C2C_Go",1)  
  wait_for_goniohead()
  
def lib_open_shutter():
  beamline_lib.mvaDescriptor("fastShutter",beamline_support.getPvValFromDescriptor("fastShutterOpenPos"))    


def lib_close_shutter():
  beamline_lib.mvaDescriptor("fastShutter",beamline_support.getPvValFromDescriptor("fastShutterClosePos"))



def lib_home():
  pass


def lib_home_omega():
  pass



def lib_home_dist():
  pass #for now


def gon_stop():
  logger.info("setting osc abort")
  beamline_support.setPvValFromDescriptor("vectorAbort",1)


def oscWait():
  time.sleep(0.15)
  while (beamline_support.getPvValFromDescriptor("oscRunning")):
    time.sleep(0.05)
  

def gon_osc(angle_start,width,exptime):

  angle_end = angle_start+width
  beamline_support.setPvValFromDescriptor("oscOmegaStart",angle_start)
  beamline_support.setPvValFromDescriptor("oscOmegaEnd",angle_end)
  beamline_support.setPvValFromDescriptor("oscDuration",exptime)
  beamline_support.setPvValFromDescriptor("oscGo",1)
  oscWait()
  end_osc = beamline_lib.motorPosFromDescriptor("omega")
  logger.info("end_osc in gon_osc = " + str(end_osc) + "\n")
  return end_osc


def wait_for_goniohead(): #why can't I just call wait_motors????
  while (1):
    try:
      done_stat = beamline_support.getPvValFromDescriptor("gonioDone")
      if (done_stat != 0):
        break
      else:
        time.sleep(.2)
        pass      
    except KeyboardInterrupt:
      pass
    except CaChannelException as status:
      logger.error(ca.message(status))
      logger.error("\n\nHandled Epics Error in wait for motors-2\n\n")
      continue
  
  
