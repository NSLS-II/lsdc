from ophyd import PVPositioner, PVPositionerPC, Device, Component as Cpt, EpicsMotor, EpicsSignal, EpicsSignalRO

class Transmission(Device):
    energy = Cpt(EpicsSignal, 'Energy-SP') # PV only used for debugging. Attenuator uses Bragg axis energy
    transmission = Cpt(EpicsSignal, 'Trans-SP')
    set_trans = Cpt(EpicsSignal, 'Cmd:Set-Cmd.PROC')

## Dummy Attenuator - for read/write_lut() and XF:17ID-ES:FMX{Misc-LUT:atten}X-Wfm/Y-Wfm
class AttenuatorLUT(Device):
    done = Cpt(EpicsSignalRO, '}attenDone')

class AttenuatorBCU(Device):
    a1 = Cpt(EpicsMotor, '-Ax:1}Mtr', labels=['fmx'])
    a2 = Cpt(EpicsMotor, '-Ax:2}Mtr', labels=['fmx'])
    a3 = Cpt(EpicsMotor, '-Ax:3}Mtr', labels=['fmx'])
    a4 = Cpt(EpicsMotor, '-Ax:4}Mtr', labels=['fmx'])
    done = Cpt(EpicsSignalRO, '}attenDone')

class RISlider(Device):
    mv_in = Cpt(EpicsSignal, 'Cmd:In-Cmd')
    mv_out = Cpt(EpicsSignal, 'Cmd:Out-Cmd')
    status = Cpt(EpicsSignalRO, 'Pos-Sts') # status: 0 (Not In), 1 (In)
    
class AttenuatorRI(Device):
    f1 = Cpt(RISlider, '01}')
    f2 = Cpt(RISlider, '02}')
    f3 = Cpt(RISlider, '03}')
    f4 = Cpt(RISlider, '04}')
    f5 = Cpt(RISlider, '05}')
    f6 = Cpt(RISlider, '06}')
    f7 = Cpt(RISlider, '07}')
    f8 = Cpt(RISlider, '08}')
    f9 = Cpt(RISlider, '09}')
    f10 = Cpt(RISlider, '10}')
    f11 = Cpt(RISlider, '11}')
    f12 = Cpt(RISlider, '12}')

class Transfocator(Device):
    c1 = Cpt(RISlider, '01}')
    c2 = Cpt(RISlider, '02}')
    c3 = Cpt(RISlider, '03}')
    c4 = Cpt(RISlider, '04}')
    c5 = Cpt(RISlider, '05}')
    c6 = Cpt(RISlider, '06}')
    c7 = Cpt(RISlider, '07}')
    c8 = Cpt(RISlider, '08}')
    c9 = Cpt(RISlider, '09}')
    c10 = Cpt(RISlider, '10}')
    c11 = Cpt(RISlider, '11}')
    c12 = Cpt(RISlider, '12}')
    vs = Cpt(RISlider, '02}')  # 1st bank with V slit
    v2a = Cpt(RISlider, '04}') # 1st bank with 2 V lenses
    v1a = Cpt(RISlider, '06}') # 1st bank with 1 V lens
    v1b = Cpt(RISlider, '08}') # 2nd bank with 1 V lens
    hs = Cpt(RISlider, '01}')  # 1st bank with H slit
    h4a = Cpt(RISlider, '03}') # 1st bank with 4 H lenses
    h2a = Cpt(RISlider, '05}') # 1st bank with 2 H lenses
    h1a = Cpt(RISlider, '07}') # 1st bank with 1 H lens
    h1b = Cpt(RISlider, '09}') # 2nd bank with 1 H lens

#######################################################
### FMX
#######################################################


## BCU Transmission
trans_bcu = Transmission('XF:17IDC-OP:FMX{Attn:BCU}', name='trans_bcu',
                         read_attrs=['transmission'])
## RI Transmission
trans_ri = Transmission('XF:17IDC-OP:FMX{Attn:RI}', name='trans_ri',
                        read_attrs=['transmission'])

## Dummy Attenuator - for read/write_lut() and XF:17ID-ES:FMX{Misc-LUT:atten}X-Wfm/Y-Wfm
atten = AttenuatorLUT('XF:17IDC-OP:FMX{Attn:BCU', name='atten',
                          read_attrs=['done'])

## BCU Attenuator
atten_bcu = AttenuatorBCU('XF:17IDC-OP:FMX{Attn:BCU', name='atten_bcu',
                          read_attrs=['done', 'a1', 'a2', 'a3', 'a4'],
                          labels=['fmx'])

## RI Attenuator
atten_ri = AttenuatorRI('XF:17IDC-OP:FMX{Attn:', name='atten_ri',
                        read_attrs=[],
                        labels=['fmx'])

## RI Transfocator
transfocator = Transfocator('XF:17IDC-OP:FMX{CRL:', name='transfocator',
                            read_attrs=[],
                            labels=['fmx'])
