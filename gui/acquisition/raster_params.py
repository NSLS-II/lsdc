from qtpy import QtWidgets, QtCore, QtGui
from enum import Enum
import typing
import db_lib, daq_utils

if typing.TYPE_CHECKING:
    from gui.control_main import ControlMain


class RasterStep(float, Enum):
    COARSE = 20.0
    FINE = 10.0
    VFINE = 5.0


class RasterParamsFrame(QtWidgets.QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.rasterStep: float = RasterStep.COARSE.value

        self.vBoxRasterParams = QtWidgets.QVBoxLayout()
        self.hBoxRasterLayout1 = QtWidgets.QHBoxLayout()
        self.hBoxRasterLayout1.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.hBoxRasterLayout2 = QtWidgets.QHBoxLayout()
        self.hBoxRasterLayout2.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        rasterStepLabel = QtWidgets.QLabel("Raster Step")
        rasterStepLabel.setFixedWidth(110)
        self.rasterStepEdit = QtWidgets.QLineEdit(str(RasterStep.COARSE.value))
        self.rasterStepEdit.setValidator(QtGui.QDoubleValidator())
        self.rasterStepEdit.textChanged.connect(self.rasterStepChanged)
        self.rasterStepEdit.setFixedWidth(60)
        self.rasterGrainRadioGroup = QtWidgets.QButtonGroup()
        self.rasterGrainCoarseRadio = QtWidgets.QRadioButton("Coarse")
        self.rasterGrainCoarseRadio.setChecked(False)
        self.rasterGrainCoarseRadio.toggled.connect(
            lambda: self.rasterGrainToggledCB(RasterStep.COARSE)
        )
        self.rasterGrainRadioGroup.addButton(self.rasterGrainCoarseRadio)
        self.rasterGrainFineRadio = QtWidgets.QRadioButton("Fine")
        self.rasterGrainFineRadio.setChecked(False)
        self.rasterGrainFineRadio.toggled.connect(
            lambda: self.rasterGrainToggledCB(RasterStep.FINE)
        )
        self.rasterGrainRadioGroup.addButton(self.rasterGrainFineRadio)
        self.rasterGrainVFineRadio = QtWidgets.QRadioButton("VFine")
        self.rasterGrainVFineRadio.setChecked(False)
        self.rasterGrainVFineRadio.toggled.connect(
            lambda: self.rasterGrainToggledCB(RasterStep.VFINE)
        )
        self.rasterGrainRadioGroup.addButton(self.rasterGrainVFineRadio)
        self.rasterGrainCustomRadio = QtWidgets.QRadioButton("Custom")
        self.rasterGrainCustomRadio.setChecked(True)
        self.rasterGrainCustomRadio.toggled.connect(
            lambda: self.rasterStepChanged(self.rasterStepEdit.text())
        )
        self.rasterGrainRadioGroup.addButton(self.rasterGrainCustomRadio)
        rasterEvalLabel = QtWidgets.QLabel("Raster\nEvaluate By:")
        rasterEvalOptionList = ["Spot Count", "Resolution", "Intensity"]
        self.rasterEvalComboBox = QtWidgets.QComboBox(self)
        self.rasterEvalComboBox.addItems(rasterEvalOptionList)
        self.rasterEvalComboBox.setCurrentIndex(
            db_lib.beamlineInfo(daq_utils.beamline, "rasterScoreFlag")["index"]
        )
        self.rasterEvalComboBox.activated.connect(self.rasterEvalComboActivatedCB)
        self.hBoxRasterLayout1.addWidget(rasterStepLabel)
        self.hBoxRasterLayout1.addWidget(self.rasterStepEdit)
        self.hBoxRasterLayout1.addWidget(self.rasterGrainCoarseRadio)
        self.hBoxRasterLayout1.addWidget(self.rasterGrainFineRadio)
        self.hBoxRasterLayout1.addWidget(self.rasterGrainVFineRadio)
        self.hBoxRasterLayout1.addWidget(self.rasterGrainCustomRadio)
        self.hBoxRasterLayout1.addWidget(rasterEvalLabel)
        self.hBoxRasterLayout1.addWidget(self.rasterEvalComboBox)
        self.vBoxRasterParams.addLayout(self.hBoxRasterLayout1)
        self.vBoxRasterParams.addLayout(self.hBoxRasterLayout2)
        self.setLayout(self.vBoxRasterParams)

    def rasterGrainToggledCB(self, identifier: RasterStep):
        self.rasterStepEdit.setText(str(identifier.value))
        self.rasterStep = identifier.value

    def rasterStepChanged(self, text):
        self.rasterStep = float(text)

    def rasterEvalComboActivatedCB(self, text):
        db_lib.beamlineInfo(
            daq_utils.beamline,
            "rasterScoreFlag",
            info_dict={"index": self.rasterEvalComboBox.findText(str(text))},
        )
        if self.parent().currentRasterCellList != []:
            self.parent().reFillPolyRaster()

    def parent(self):
        return typing.cast("ControlMain", super().parent())

    def setGridStep(self, value: float):
        self.rasterStepEdit.setText(str(value))
        if value == RasterStep.COARSE:
            self.rasterGrainCoarseRadio.setChecked(True)
        elif value == RasterStep.FINE:
            self.rasterGrainFineRadio.setChecked(True)
        elif value == RasterStep.VFINE:
            self.rasterGrainVFineRadio.setChecked(True)
        else:
            self.rasterGrainCustomRadio.setChecked(True)
