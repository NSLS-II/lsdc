from ophyd import PVPositioner, PVPositionerPC, Device, Component as Cpt, EpicsMotor, EpicsSignal, EpicsSignalRO

class XYMotor(Device):
	x = Cpt(EpicsMotor, '-Ax:X}Mtr')
	y = Cpt(EpicsMotor, '-Ax:Y}Mtr')


class XYZMotor(XYMotor):
	z = Cpt(EpicsMotor, '-Ax:Z}Mtr')


class XYPitchMotor(XYMotor):
	pitch = Cpt(EpicsMotor, '-Ax:P}Mtr')


class XZXYMotor(Device):
	x = Cpt(EpicsMotor, '-Ax:X}Mtr')
	z = Cpt(EpicsMotor, '-Ax:Z}Mtr')


class XYZfMotor(Device):
	x = Cpt(EpicsMotor, '-Ax:Xf}Mtr')
	y = Cpt(EpicsMotor, '-Ax:Yf}Mtr')
	z = Cpt(EpicsMotor, '-Ax:Zf}Mtr')


class YMotor(Device):
	y = Cpt(EpicsMotor, '-Ax:Y}Mtr')


class Slits(Device):
	b = Cpt(EpicsMotor, '-Ax:B}Mtr', labels=['fmx'])
	i = Cpt(EpicsMotor, '-Ax:I}Mtr', labels=['fmx'])
	o = Cpt(EpicsMotor, '-Ax:O}Mtr', labels=['fmx'])
	t = Cpt(EpicsMotor, '-Ax:T}Mtr', labels=['fmx'])
	x_ctr = Cpt(EpicsMotor, '-Ax:XCtr}Mtr', labels=['fmx'])
	x_gap = Cpt(EpicsMotor, '-Ax:XGap}Mtr', labels=['fmx'])
	y_ctr = Cpt(EpicsMotor, '-Ax:YCtr}Mtr', labels=['fmx'])
	y_gap = Cpt(EpicsMotor, '-Ax:YGap}Mtr', labels=['fmx'])


class VirtualCenter(PVPositioner):
	setpoint = Cpt(EpicsSignal, 'center')
	readback = Cpt(EpicsSignalRO, 't2.D')
	done = Cpt(EpicsSignalRO, 'DMOV')
	done_value = 1


class VirtualGap(PVPositioner):
	setpoint = Cpt(EpicsSignal, 'size')
	readback = Cpt(EpicsSignalRO, 't2.C')
	done = Cpt(EpicsSignalRO, 'DMOV')
	done_value = 1


class FESlits(Device):
	i = Cpt(EpicsMotor, '{Slt:3-Ax:I}Mtr')
	t = Cpt(EpicsMotor, '{Slt:3-Ax:T}Mtr')
	o = Cpt(EpicsMotor, '{Slt:4-Ax:O}Mtr')
	b = Cpt(EpicsMotor, '{Slt:4-Ax:B}Mtr')
	x_ctr = Cpt(VirtualCenter, '{Slt:34-Ax:X}')
	y_ctr = Cpt(VirtualCenter, '{Slt:34-Ax:Y}')
	x_gap = Cpt(VirtualGap,    '{Slt:34-Ax:X}')
	y_gap = Cpt(VirtualGap,    '{Slt:34-Ax:Y}')


class HorizontalDCM(Device):
	b = Cpt(EpicsMotor, '-Ax:B}Mtr')
	g = Cpt(EpicsMotor, '-Ax:G}Mtr')
	p = Cpt(EpicsMotor, '-Ax:P}Mtr')
	r = Cpt(EpicsMotor, '-Ax:R}Mtr')
	e = Cpt(EpicsMotor, '-Ax:E}Mtr')
	w = Cpt(EpicsMotor, '-Ax:W}Mtr')


class KBMirror(Device):
	hp = Cpt(EpicsMotor, ':KBH-Ax:P}Mtr')
	hr = Cpt(EpicsMotor, ':KBH-Ax:R}Mtr')
	hx = Cpt(EpicsMotor, ':KBH-Ax:X}Mtr')
	hy = Cpt(EpicsMotor, ':KBH-Ax:Y}Mtr')
	vp = Cpt(EpicsMotor, ':KBV-Ax:P}Mtr')
	vx = Cpt(EpicsMotor, ':KBV-Ax:X}Mtr')
	vy = Cpt(EpicsMotor, ':KBV-Ax:Y}Mtr')


class GoniometerStack(Device):
	gx = Cpt(EpicsMotor, '-Ax:GX}Mtr')
	gy = Cpt(EpicsMotor, '-Ax:GY}Mtr')
	gz = Cpt(EpicsMotor, '-Ax:GZ}Mtr')
	o  = Cpt(EpicsMotor, '-Ax:O}Mtr')
	py = Cpt(EpicsMotor, '-Ax:PY}Mtr')
	pz = Cpt(EpicsMotor, '-Ax:PZ}Mtr')

class ShutterTranslation(Device):
	x = Cpt(EpicsMotor, '-Ax:X}Mtr')

class BeamStop(Device):
	fx = Cpt(EpicsMotor, '-Ax:FX}Mtr')
	fy = Cpt(EpicsMotor, '-Ax:FY}Mtr')
    
class Cover(Device):
    close = Cpt(EpicsSignal, 'Cmd:Cls-Cmd')
    open = Cpt(EpicsSignal, 'Cmd:Opn-Cmd')
    status = Cpt(EpicsSignalRO, 'Pos-Sts') # status: 0 (Not Open), 1 (Open)

class Shutter(Device):
    close = Cpt(EpicsSignal, 'Cmd:Cls-Cmd.PROC')
    open = Cpt(EpicsSignal, 'Cmd:Opn-Cmd.PROC')
    status = Cpt(EpicsSignalRO, 'Pos-Sts') # status: 0 (Open), 1 (Closed), 2 (Undefined)
    

#######################################################
### FMX
#######################################################

## High Heat Load Slits
hhls = Slits('XF:17IDA-OP:FMX{Slt:0', name='hhls', labels=['fmx'])

## Horizontal Double Crystal Monochromator
hdcm = HorizontalDCM('XF:17IDA-OP:FMX{Mono:DCM', name='hdcm')

## Horizontal Focusing Mirror - XYPitchMotor
hfm = XYPitchMotor('XF:17IDA-OP:FMX{Mir:HFM', name='hfm')

## BPM Motions
mbpm1 = XYMotor('XF:17IDA-BI:FMX{BPM:1', name='mbpm1')
mbpm2 = XYMotor('XF:17IDC-BI:FMX{BPM:2', name='mbpm2')
mbpm3 = XYMotor('XF:17IDC-BI:FMX{BPM:3', name='mbpm3')

## Slits Motions
slits1 = Slits('XF:17IDA-OP:FMX{Slt:1', name='slits1', labels=['fmx'])
slits2 = Slits('XF:17IDC-OP:FMX{Slt:2', name='slits2', labels=['fmx'])
slits3 = Slits('XF:17IDC-OP:FMX{Slt:3', name='slits3', labels=['fmx'])
slits4 = Slits('XF:17IDC-OP:FMX{Slt:4', name='slits4', labels=['fmx'])

## KB Mirror
kbm = KBMirror('XF:17IDC-OP:FMX{Mir', name='kbm')

## Microscope
mic = XYMotor('XF:17IDC-ES:FMX{Mic:1', name='mic')
light = YMotor('XF:17IDC-ES:FMX{Light:1', name='lightY')

## Goniometer Stack
gonio = GoniometerStack('XF:17IDC-ES:FMX{Gon:1', name='gonio')

## Beam Conditioning Unit Shutter Translation
sht = ShutterTranslation('XF:17IDC-ES:FMX{Sht:1', name='sht')

## FE Slits
fe = FESlits('FE:C17A-OP', name='fe')

## Holey Mirror
hm = XYZMotor('XF:17IDC-ES:FMX{Mir:1', name='hm')

## Beam Stop
bs = BeamStop('XF:17IDC-ES:FMX{BS:1', name='bs')

## Collimator
colli = XZXYMotor('XF:17IDC-ES:FMX{Colli:1', name='colli')

## PI Scanner Fine Stages
pif = XYZfMotor('XF:17IDC-ES:FMX{Gon:1', name='pif')

## Eiger16M detector cover
cover_detector = Cover('XF:17IDC-ES:FMX{Det:FMX-Cover}', name='cover_detector',
                 read_attrs=['status'])

## 17-ID-A FOE shutter
shutter_foe = Shutter('XF:17ID-PPS:FAMX{Sh:FE}', name='shutter_foe',
                 read_attrs=['status'])

## 17-ID-C experimental hutch shutter
shutter_hutch_c = Shutter('XF:17IDA-PPS:FMX{PSh}', name='shutter_hutch_c',
                 read_attrs=['status'])

## FMX BCU shutter
shutter_bcu = Shutter('XF:17IDC-ES:FMX{Gon:1-Sht}', name='shutter_bcu',
                 read_attrs=['status'])


