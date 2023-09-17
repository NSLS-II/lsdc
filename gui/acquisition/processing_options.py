from qtpy import QtWidgets, QtCore


class ProcessingOptionsFrame(QtWidgets.QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.hBoxProcessingLayout1 = QtWidgets.QHBoxLayout()
        self.hBoxProcessingLayout1.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        procOptionLabel = QtWidgets.QLabel("Processing Options:")
        procOptionLabel.setFixedWidth(200)
        self.autoProcessingCheckBox = QtWidgets.QCheckBox("AutoProcessing On")
        self.autoProcessingCheckBox.setChecked(True)
        self.autoProcessingCheckBox.stateChanged.connect(self.autoProcessingCheckCB)
        self.fastEPCheckBox = QtWidgets.QCheckBox("FastEP")
        self.fastEPCheckBox.setChecked(False)
        self.fastEPCheckBox.setEnabled(False)
        self.dimpleCheckBox = QtWidgets.QCheckBox("Dimple")
        self.dimpleCheckBox.setChecked(True)
        self.xia2CheckBox = QtWidgets.QCheckBox("Xia2")
        self.xia2CheckBox.setChecked(False)
        self.hBoxProcessingLayout1.addWidget(self.autoProcessingCheckBox)
        self.hBoxProcessingLayout1.addWidget(self.fastEPCheckBox)
        self.hBoxProcessingLayout1.addWidget(self.dimpleCheckBox)
        self.setLayout(self.hBoxProcessingLayout1)

    def autoProcessingCheckCB(self, state):
        if state == QtCore.Qt.CheckState.Checked:
            self.dimpleCheckBox.setEnabled(True)
            self.xia2CheckBox.setEnabled(True)
        else:
            self.fastEPCheckBox.setEnabled(False)
            self.dimpleCheckBox.setEnabled(False)
            self.xia2CheckBox.setEnabled(False)
