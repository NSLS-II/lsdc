from ophyd import (Component as Cpt, EpicsSignal, EpicsSignalRO, Device)


class ZebraPCBase(Device):
    sel = Cpt(EpicsSignal, 'SEL', kind="config", auto_monitor=True)
    start = Cpt(EpicsSignal, 'START', kind="config", auto_monitor=True)
    width = Cpt(EpicsSignal, 'WID', kind="config", auto_monitor=True)
    step = Cpt(EpicsSignal, 'STEP', kind="config", auto_monitor=True)


class ZebraPCGate(ZebraPCBase):
    num_gates = Cpt(EpicsSignal, 'NGATE', kind="config", auto_monitor=True)


class ZebraPCPulse(ZebraPCBase):
    max = Cpt(EpicsSignal, 'MAX', kind="config", auto_monitor=True)
    delay = Cpt(EpicsSignal, 'DLY', kind="config", auto_monitor=True)
    status = Cpt(EpicsSignalRO, 'INP.STA', kind="omitted")


class ZebraPositionCompare(Device):
    arm_status = Cpt(EpicsSignalRO, 'ARM_INP.STA', kind="omitted")
    arm_sel = Cpt(EpicsSignal, 'ARM_SEL', kind="omitted")
    download_count = Cpt(EpicsSignalRO, 'NUM_DOWN', kind="omitted")
    disarm = Cpt(EpicsSignal, 'DISARM', kind="omitted")
    encoder = Cpt(EpicsSignal, 'ENC', kind="config", auto_monitor=True)
    enc_x = Cpt(EpicsSignal, 'ENC1', kind="omitted")
    enc_y = Cpt(EpicsSignal, 'ENC2', kind="omitted")
    enc_z = Cpt(EpicsSignal, 'ENC3', kind="omitted")
    enc_omega = Cpt(EpicsSignal, 'ENC4', kind="omitted")
    direction = Cpt(EpicsSignal, 'DIR', kind="config", auto_monitor=True)
    gate = Cpt(ZebraPCGate, 'GATE_', kind="config")
    pulse = Cpt(ZebraPCPulse, 'PULSE_')


class ZebraAnd(Device):
    inp1 = Cpt(EpicsSignal, 'INP1:STA', kind="omitted")
    inp2 = Cpt(EpicsSignal, 'INP2:STA', kind="omitted")

class Zebra(Device):
    downloading = Cpt(EpicsSignal, 'ARRAY_ACQ', kind="omitted")
    reset = Cpt(EpicsSignal, 'SYS_RESET.PROC', kind="omitted")
    m1_set_pos = Cpt(EpicsSignal, 'M1:SETPOS.PROC', kind="omitted")
    m2_set_pos = Cpt(EpicsSignal, 'M2:SETPOS.PROC', kind="omitted")
    m3_set_pos = Cpt(EpicsSignal, 'M3:SETPOS.PROC', kind="omitted")
    m4_set_pos = Cpt(EpicsSignal, 'M4:SETPOS.PROC', kind="omitted")
    out1 = Cpt(EpicsSignal, 'OUT1_TTL', kind="config", auto_monitor=True)
    pc = Cpt(ZebraPositionCompare, 'PC_')
    and1 = Cpt(ZebraAnd, 'AND1_')
