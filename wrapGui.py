#!/opt/conda_envs/lsdc-gui-2023-2-latest/bin/python
"""
If lsdcGui is stopped abnormally, restart it!
"""
import os
from epics import PV
import db_lib

def check_pid(pid):
  try:
    os.kill(pid, 0)
  except OSError:
    return False
  else:
    return True

returnStat = (os.system("$LSDCHOME/lsdcGui.py"))
if (returnStat == 0):
  exit(1) #a normal termination, no further work needed, else figure out who is master and restart
beamline = os.environ["BEAMLINE_ID"]
beamlineComm = db_lib.getBeamlineConfigParam(beamline,"beamlineComm")
controlMaster_pv = PV(beamlineComm + "zinger_flag")
for i in range (0,4):
  if (returnStat == 0): #normal exit, else restart
    break
  currentMasterPid = controlMaster_pv.get()
  if (check_pid(int(currentMasterPid))):
    returnStat = (os.system("$LSDCHOME/lsdcGui.py"))
  else:
    returnStat = (os.system("$LSDCHOME/lsdcGui.py master"))

    
