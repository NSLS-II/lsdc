from ophyd import Component as Cpt
from ophyd import Device, EpicsMotor, EpicsSignal
from mxbluesky.devices import standardize_readback

class WorkPositions(Device):
    gx = Cpt(EpicsSignal, "{Gov:Robot-Dev:gx}Pos:Work-Pos")
    gpy = Cpt(EpicsSignal, "{Gov:Robot-Dev:gpy}Pos:Work-Pos")
    gpz = Cpt(EpicsSignal, "{Gov:Robot-Dev:gpz}Pos:Work-Pos")
    o = Cpt(EpicsSignal, "{Gov:Robot-Dev:go}Pos:Work-Pos")


class MountPositions(Device):
    gx = Cpt(EpicsSignal, "{Gov:Robot-Dev:gx}Pos:Mount-Pos")
    py = Cpt(EpicsSignal, "{Gov:Robot-Dev:gpy}Pos:Mount-Pos")
    pz = Cpt(EpicsSignal, "{Gov:Robot-Dev:gpz}Pos:Mount-Pos")
    o = Cpt(EpicsSignal, "{Gov:Robot-Dev:go}Pos:Mount-Pos")

@standardize_readback
class GoniometerStack(Device):
    gx = Cpt(EpicsMotor, "-Ax:GX}Mtr")
    gy = Cpt(EpicsMotor, "-Ax:GY}Mtr")
    gz = Cpt(EpicsMotor, "-Ax:GZ}Mtr")
    o = Cpt(EpicsMotor, "-Ax:O}Mtr")
    py = Cpt(EpicsMotor, "-Ax:PY}Mtr")
    pz = Cpt(EpicsMotor, "-Ax:PZ}Mtr")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Renaming to match MD2 GonioDevice
        self.x = self.gx
        self.cx = self.gx
        self.y = self.py
        self.cy = self.py
        self.z = self.pz
        self.cz = self.pz
        self.omega = self.o