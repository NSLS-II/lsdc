from qtpy import QtWidgets
from qtpy.QtGui import QIntValidator
import typing

if typing.TYPE_CHECKING:
    from gui.control_main import ControlMain


class VectorParamsFrame(QtWidgets.QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        hBoxVectorLayout1 = QtWidgets.QHBoxLayout()
        setVectorStartButton = QtWidgets.QPushButton("Vector\nStart")
        setVectorStartButton.setStyleSheet("background-color: blue")
        setVectorStartButton.clicked.connect(
            lambda: self.parent().setVectorPointCB("vectorStart")
        )
        setVectorEndButton = QtWidgets.QPushButton("Vector\nEnd")
        setVectorEndButton.setStyleSheet("background-color: red")
        setVectorEndButton.clicked.connect(
            lambda: self.parent().setVectorPointCB("vectorEnd")
        )
        self.vecLine = None
        vectorFPPLabel = QtWidgets.QLabel("Number of Wedges")
        self.vectorFPP_ledit = QtWidgets.QLineEdit("1")
        self.vectorFPP_ledit.setValidator(QIntValidator(self))
        vecLenLabel = QtWidgets.QLabel("    Length(microns):")
        self.vecLenLabelOutput = QtWidgets.QLabel("---")
        vecSpeedLabel = QtWidgets.QLabel("    Speed(microns/s):")
        self.vecSpeedLabelOutput = QtWidgets.QLabel("---")
        hBoxVectorLayout1.addWidget(setVectorStartButton)
        hBoxVectorLayout1.addWidget(setVectorEndButton)
        hBoxVectorLayout1.addWidget(vectorFPPLabel)
        hBoxVectorLayout1.addWidget(self.vectorFPP_ledit)
        hBoxVectorLayout1.addWidget(vecLenLabel)
        hBoxVectorLayout1.addWidget(self.vecLenLabelOutput)
        hBoxVectorLayout1.addWidget(vecSpeedLabel)
        hBoxVectorLayout1.addWidget(self.vecSpeedLabelOutput)
        self.setLayout(hBoxVectorLayout1)

    def parent(self):
        return typing.cast("ControlMain", super().parent())

