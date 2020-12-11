from ophyd import (Component as Cpt, EpicsSignal, EpicsSignalRO, Device)

class ZebraPCGate(Device):
    sel = Cpt(EpicsSignal, 'SEL')
    start = Cpt(EpicsSignal, 'START')
    width = Cpt(EpicsSignal, 'WID')
    step = Cpt(EpicsSignal, 'STEP')
    num_gates = Cpt(EpicsSignal, 'NGATE')

class ZebraPCPulse(Device):
    sel = Cpt(EpicsSignal, 'SEL')
    start = Cpt(EpicsSignal, 'START')
    width = Cpt(EpicsSignal, 'WID')
    step = Cpt(EpicsSignal, 'STEP')
    max = Cpt(EpicsSignal, 'MAX')
    delay = Cpt(EpicsSignal, 'DLY')
    status = Cpt(EpicsSignalRO, 'INP.STA')

class ZebraPositionCompare(Device):
    armStatus = Cpt(EpicsSignalRO, 'ARM_INP.STA')
    downloadCount = Cpt(EpicsSignalRO, 'NUM_DOWN')
    disarm = Cpt(EpicsSignal, 'DISARM')
    encoder = Cpt(EpicsSignal, 'ENC')
    encX = Cpt(EpicsSignal, 'ENC1')
    encY = Cpt(EpicsSignal, 'ENC2')
    encZ = Cpt(EpicsSignal, 'ENC3')
    enzO = Cpt(EpicsSignal, 'ENC4')
    encoder = Cpt(EpicsSignal, 'ENC')
    direction = Cpt(EpicsSignal, 'DIR')
    gate = Cpt(ZebraPCGate, 'GATE_')
    pulse = Cpt(ZebraPCPulse, 'PULSE_')

class ZebraAnd(Device):
    inp1 = Cpt(EpicsSignal, 'INP1:STA')
    inp2 = Cpt(EpicsSignal, 'INP2:STA')
    out1 = Cpt(EpicsSignal, 'OUT1_TTL') #out type?

class Zebra(Device):
    downloading = Cpt(EpicsSignal, 'ARRAY_ARQ')
    reset = Cpt(EpicsSignal, 'SYS_RESET.PROC')
    m1SetPos = Cpt(EpicsSignal, 'M1:SETPOS.PROC')
    m2SetPos = Cpt(EpicsSignal, 'M2:SETPOS.PROC')
    m3SetPos = Cpt(EpicsSignal, 'M3:SETPOS.PROC')
    m4SetPos = Cpt(EpicsSignal, 'M4:SETPOS.PROC')
    pc = Cpt(ZebraPositionCompare, 'PC_')
    zebraAnd = Cpt(ZebraAnd, 'AND1_')
