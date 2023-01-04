''' Originally FMX's annealer code from the file 2021-02-02 FMX annealer 4 Jun.html'''
import logging
logger = logging.getLogger(__name__)
import epics
import time

import daq_utils

def blStrGet():
    """
    Return beamline string
   
    blStr: 'AMX' or 'FMX'
   
    Beamline is determined by querying hostname
    """
    if daq_utils.beamline == 'fmx':
        blStr = 'XF:17IDC-ES:FMX'
    elif daq_utils.beamline == 'amx':
        blStr = 'XF:17IDB-ES:AMX'
    else:
        logger.error('Error - this code is only available in AMX and FMX')
        blStr = -1

    return blStr

def govMsgGet(configStr = 'Robot'): #TODO Replace these functions with the Ophyd versions
    """
    Returns Governor message



    configStr: Governor configuration, 'Robot' or 'Human', default: 'Robot'

    Examples:
    govMsgGet()
    govMsgGet(configStr = 'Human')
    """
    blStr = blStrGet()
    if blStr == -1: return -1

    devStr = '{Gov:' + configStr + '}'
    stsStr = 'Sts:Msg-Sts'
    pvStr = blStr + devStr + stsStr
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

    devStr = '{Gov:' + configStr + '-St:' + stateStr + '}'
    stsStr = 'Sts:Active-Sts'
    pvStr = blStr + devStr + stsStr
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

    devStr = '{Gov:' + configStr + '}'
    cmdStr = 'Cmd:Go-Cmd'
    pvStr = blStr + devStr + cmdStr
    logger.debug(f'governor PV: {pvStr}')
    epics.caput(pvStr, stateStr)

    while not govStatusGet(stateStr, configStr = configStr):
        print(govMsgGet(configStr = configStr))
        time.sleep(2)
    print(govMsgGet(configStr = configStr))
    
    return

from ophyd import PVPositioner, PVPositionerPC, Device, Component as Cpt, EpicsMotor, EpicsSignal, EpicsSignalRO
from ophyd import SubscriptionStatus

# XF:17IDC-ES:FMX{Wago:1}AnnealerIn-Sts
# XF:17IDC-ES:FMX{Wago:1}AnnealerAir-Sel
        
## DONE Redo ophyd object with proper PV
class FmxAnnealer(Device):
    air = Cpt(EpicsSignal, '1}AnnealerAir-Sel')
    inStatus = Cpt(EpicsSignalRO, '2}AnnealerIn-Sts') # status: 0 (Not In), 1 (In)
    outStatus = Cpt(EpicsSignalRO, '2}AnnealerOut-Sts') # status: 0 (Not In), 1 (In)

    def anneal(self, anneal_time):
        def status_callback(value, old_value, **kwargs):
            if old_value == 0 and value == 1:
                return True
            else:
                return False

        status = SubscriptionStatus(self.inStatus, status_callback, run=False)
        self.air.put(1)
        status.wait(5)
        time.sleep(anneal_time)

        status = SubscriptionStatus(self.outStatus, status_callback, run=False)
        self.air.put(0)
        status.wait(5)


class AmxAnnealer(Device):
    air = Cpt(EpicsSignal, '1}AnnealerAir-Sel')
    inStatus = Cpt(EpicsSignalRO, '2}AnnealerIn-Sts') # status: 0 (Not In), 1 (In)

    def anneal(self, anneal_time):
        def in_callback(value, old_value, **kwargs):
            if old_value == 0 and value == 1:
                logger.info(f'anneal state while annealing: {value.get()}')
                return True
            else:
                logger.debug(f'anneal state before annealing: {value.get()}')
                return False
        def out_callback(value, old_value, **kwargs):
            if old_value == 1 and value == 0:
                logger.info(f'anneal state while annealing: {value.get()}')
                return True
            else:
                logger.debug(f'anneal state before annealing: {value.get()}')
                return False

        status = SubscriptionStatus(self.inStatus, in_callback, run=False)
        self.air.put(1)
        status.wait(5)
        time.sleep(anneal_time)

        status = SubscriptionStatus(self.inStatus, out_callback, run=False)
        self.air.put(0)
        status.wait(5)

## FMX annealer aka cryo blocker
fmxAnnealer = FmxAnnealer('XF:17IDC-ES:FMX{Wago:', name='annealer',
                        read_attrs=[],
                        labels=['fmx'])

amxAnnealer = AmxAnnealer('XF:17IDB-ES:AMX{Wago:', name='annealer',
                        read_attrs=[],
                        labels=['amx'])
