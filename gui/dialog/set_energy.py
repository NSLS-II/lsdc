import logging
import typing

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt

import daq_utils
import db_lib
import setenergy_lsdc

if typing.TYPE_CHECKING:
    from lsdcGui import ControlMain

logger = logging.getLogger()


class SetEnergyDialog(QtWidgets.QDialog):
    def __init__(self, parent: "ControlMain"):
        super().__init__(parent)

    def initUI(self):
        layout = QtWidgets.QGridLayout()
        self.current_energy_label = QtWidgets.QLabel("Current Energy: ")
        self.current_energy_value = QtWidgets.QLabel("0 eV")
        layout.addWidget(self.current_energy_label, 0, 0)
        layout.addWidget(self.current_energy_value, 0, 1)

        setenergy_lsdc.hdcm.e.user_readback.subscribe(self.update_energy, run=True)

    def update_energy(self, value):
        print(value)
