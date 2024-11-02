from ophyd import Component as Cpt
from ophyd import Device, EpicsMotor, EpicsSignal


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


class Dewar(Device):
    rotation = Cpt(EpicsSignal, "{Dew:1-Ax:R}Virtual")
    rotation_motor = Cpt(EpicsMotor, "{Dew:1-Ax:R}Mtr")

    def rotate(self, rotation_angle, absolute=True):
        def check_value_sink(*, old_value, value, **kwargs):
            "Return True when the movement is complete, False otherwise."
            return old_value == 1 and value == 0

        def check_value_raise(*, old_value, value, **kwargs):
            "Return True when the movement is started, False otherwise."
            return old_value == 0 and value == 1

        status = SubscriptionStatus(
            self.rotation_motor.motor_done_move, check_value_sink
        )
        if not self.rotation_motor.motor_done_move.get():
            raise RuntimeError("Dewar rotation motor already moving.")
            ### Maybe don't raise an error here but rather do a timeout retry?
        if absolute:
            self.rotation.set(rotation_angle)
        else:
            current_angle = self.rotation.get()
            self.rotation.set(current_angle + rotation_angle)
        status.wait()
        status = SubscriptionStatus(
            self.rotation_motor.motor_done_move, check_value_raise
        )
        status.wait()

class RobotArm(Device):
    speed = Cpt(EpicsSignal, '{EMBL}:RobotSpeed')

    def is_full_speed(self):
        # Checks if the robot speed is 100%
        if self.speed.get() < 100:
            return False
        return True
