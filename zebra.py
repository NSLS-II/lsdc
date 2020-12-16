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
    arm_status = Cpt(EpicsSignalRO, 'ARM_INP.STA')
    download_count = Cpt(EpicsSignalRO, 'NUM_DOWN')
    disarm = Cpt(EpicsSignal, 'DISARM')
    encoder = Cpt(EpicsSignal, 'ENC')
    enc_x = Cpt(EpicsSignal, 'ENC1')
    enc_y = Cpt(EpicsSignal, 'ENC2')
    enc_z = Cpt(EpicsSignal, 'ENC3')
    enz_o = Cpt(EpicsSignal, 'ENC4')
    encoder = Cpt(EpicsSignal, 'ENC')
    direction = Cpt(EpicsSignal, 'DIR')
    gate = Cpt(ZebraPCGate, 'GATE_')
    pulse = Cpt(ZebraPCPulse, 'PULSE_')

class ZebraAnd(Device):
    inp1 = Cpt(EpicsSignal, 'INP1:STA')
    inp2 = Cpt(EpicsSignal, 'INP2:STA')
    out1 = Cpt(EpicsSignal, 'OUT1_TTL')

class Zebra(Device):
    downloading = Cpt(EpicsSignal, 'ARRAY_ARQ')
    reset = Cpt(EpicsSignal, 'SYS_RESET.PROC')
    m1_set_pos = Cpt(EpicsSignal, 'M1:SETPOS.PROC')
    m2_set_pos = Cpt(EpicsSignal, 'M2:SETPOS.PROC')
    m3_set_pos = Cpt(EpicsSignal, 'M3:SETPOS.PROC')
    m4_set_pos = Cpt(EpicsSignal, 'M4:SETPOS.PROC')
    pc = Cpt(ZebraPositionCompare, 'PC_')
    zebra_and = Cpt(ZebraAnd, 'AND1_')
