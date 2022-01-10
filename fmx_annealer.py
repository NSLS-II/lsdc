''' Originally FMX's annealer code from the file 2021-02-02 FMX annealer 4 Jun.html'''
import logging
logger = logging.getLogger(__name__)
import epics
import time

import socket

def blStrGet():
    """
    Return beamline string
   
    blStr: 'AMX' or 'FMX'
   
    Beamline is determined by querying hostname
    """
    hostStr = socket.gethostname()
    if hostStr == 'xf17id2-ca1':
        blStr = 'FMX'
    elif hostStr == 'xf17id1-ca1':
        blStr = 'AMX'
    else:
        logger.error('Error - this code must be executed on one of the -ca1 machines')
        blStr = -1
       
    return blStr

def govMsgGet(configStr = 'Robot'):
    """
    Returns Governor message



    configStr: Governor configuration, 'Robot' or 'Human', default: 'Robot'

    Examples:
    govMsgGet()
    govMsgGet(configStr = 'Human')
    """
    blStr = blStrGet()
    if blStr == -1: return -1

    sysStr = 'XF:17IDC-ES:' + blStr
    devStr = '{Gov:' + configStr + '}'
    stsStr = 'Sts:Msg-Sts'
    pvStr = sysStr + devStr + stsStr
    govMsg = epics.caget(pvStr)

    return govMsg

def govStatusGet(stateStr, configStr = 'Robot'):
    """
    Returns the current active status for a Governor state
    
    configStr: Governor configuration, 'Robot' or 'Human', default: 'Robot'
    stateStr: Governor short version state. Example: 'SA' for sample alignment
              one of ['M', 'SE', 'SA', 'DA', 'XF', 'BL', 'BS', 'AB', 'CB', 'DI']

    Examples
    govStatusGet('SA')
    govStatusGet('SA', configStr = 'Human')
    """
    blStr = blStrGet()
    if blStr == -1: return -1
    
    if stateStr not in ['M', 'SE', 'SA', 'DA', 'XF', 'BL', 'BS', 'AB', 'CB', 'DI']:
        logger.error('stateStr must be one of: M, SE, SA, DA, XF, BL, BS, AB, CB, DI]')
        return -1
    
    sysStr = 'XF:17IDC-ES:' + blStr
    devStr = '{Gov:' + configStr + '-St:' + stateStr + '}'
    stsStr = 'Sts:Active-Sts'
    pvStr = sysStr + devStr + stsStr
    govStatus = epics.caget(pvStr)
    
    return govStatus

def govStateSet(stateStr, configStr = 'Robot'):
    """
    Sets Governor state

    configStr: Governor configuration, 'Robot' or 'Human', default: 'Robot'
    stateStr: Governor short version state. Example: 'SA' for sample alignment
              one of ['M', 'SE', 'SA', 'DA', 'XF', 'BL', 'BS', 'AB', 'CB', 'DI']

    Examples:
    govStateSet('SA')
    govStateSet('AB', configStr = 'Human')
    """
    blStr = blStrGet()
    if blStr == -1: return -1

    if stateStr not in ['M', 'SE', 'SA', 'DA', 'XF', 'BL', 'BS', 'AB', 'CB', 'DI']:
        logger.error('stateStr must be one of: M, SE, SA, DA, XF, BL, BS, AB, CB, DI]')
        return -1
    
    sysStr = 'XF:17IDC-ES:' + blStr
    devStr = '{Gov:' + configStr + '}'
    cmdStr = 'Cmd:Go-Cmd'
    pvStr = sysStr + devStr + cmdStr
    epics.caput(pvStr, stateStr)
    
    while not govStatusGet(stateStr, configStr = configStr):
        print(govMsgGet(configStr = configStr))
        time.sleep(2)
    print(govMsgGet(configStr = configStr))
    
    return

from ophyd import PVPositioner, PVPositionerPC, Device, Component as Cpt, EpicsMotor, EpicsSignal, EpicsSignalRO

# XF:17IDC-ES:FMX{Wago:1}AnnealerIn-Sts
# XF:17IDC-ES:FMX{Wago:1}AnnealerAir-Sel
        
## DONE Redo ophyd object with proper PV
class Annealer(Device):
    air = Cpt(EpicsSignal, '1}AnnealerAir-Sel')
    inStatus = Cpt(EpicsSignalRO, '2}AnnealerIn-Sts') # status: 0 (Not In), 1 (In)
    outStatus = Cpt(EpicsSignalRO, '2}AnnealerOut-Sts') # status: 0 (Not In), 1 (In)

## FMX annealer aka cryo blocker
annealer = Annealer('XF:17IDC-ES:FMX{Wago:', name='annealer',
                        read_attrs=[],
                        labels=['fmx'])
