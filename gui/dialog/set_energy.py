import logging
import typing

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt

import daq_utils
import db_lib
from ophyd import Component as Cpt
from ophyd import Device
from ophyd import EpicsMotor

if typing.TYPE_CHECKING:
    from lsdcGui import ControlMain

logger = logging.getLogger()

class DCM(Device):
    b = Cpt(EpicsMotor, '-Ax:B}Mtr', labels=['fmx'])
    g = Cpt(EpicsMotor, '-Ax:G}Mtr', labels=['fmx'])
    p = Cpt(EpicsMotor, '-Ax:P}Mtr', labels=['fmx'])
    r = Cpt(EpicsMotor, '-Ax:R}Mtr', labels=['fmx'])
    e = Cpt(EpicsMotor, '-Ax:E}Mtr', labels=['fmx'])



class SetEnergyDialog(QtWidgets.QDialog):
    def __init__(self, parent: "ControlMain"):
        self.hdcm = DCM('XF:17IDA-OP:FMX{Mono:DCM', name='hdcm')
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QtWidgets.QGridLayout()
        self.current_energy_label = QtWidgets.QLabel("Current Energy: ")
        self.current_energy_value_label = QtWidgets.QLabel(f"{self.hdcm.e.user_readback.get()} eV")
        layout.addWidget(self.current_energy_label, 0, 0)
        layout.addWidget(self.current_energy_value_label, 0, 1)

        self.setpoint_label = QtWidgets.QLabel("Energy setpoint: ")
        validator = QtGui.QDoubleValidator()
        self.setpoint_edit = QtWidgets.QLineEdit()
        self.setpoint_edit.setValidator(validator)
        self.setpoint_edit.returnPressed.connect(self.check_value)
        layout.addWidget(self.setpoint_label, 1, 0)
        layout.addWidget(self.setpoint_edit, 1, 1)

        self.message = QtWidgets.QLabel("")
        layout.addWidget(self.message, 2, 0, 1, 2)

        self.confirm_button = QtWidgets.QPushButton("Confirm")
        self.confirm_button.setAutoDefault(False)
        self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self.set_energy)
        
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.cancel_set_energy)

        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        self.close_button.setAutoDefault(False)

        layout.addWidget(self.confirm_button, 3, 0)
        layout.addWidget(self.cancel_button, 3, 1)
        layout.addWidget(self.close_button, 4, 0, 1, 2)

        self.hdcm.e.user_readback.subscribe(self.update_energy, run=True)

        self.setLayout(layout)
        self.setModal(True)
        self.show()

    def update_energy(self, value):
        print(value)
    
    def check_value(self):
        if abs(float(self.setpoint_edit.text()) - self.hdcm.e.user_readback.get()) > 10:
            #
            self.message.setText("Energy change is greater than 10 eV.\nConfirm by clicking button or cancel")
            self.confirm_button.setEnabled(True)
            self.setpoint_edit.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            
        else:
            comm_s = 'mvaDescriptor("energy",' + str(self.energy_ledit.text()) + ")"
            print(f"executing {comm_s}")
            # self.parent().send_to_server(comm_s)

    def set_energy(self):
        import traceback
        print("set_energy was called")
        traceback.print_stack()
        print(r'Executing: self.parent().send_to_server(f"setELsdc({self.setpoint_edit.text()})")')

    def cancel_set_energy(self):
        print("Clicked cancel")
        self.setpoint_edit.setEnabled(True)
        self.confirm_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

