from qtpy import QtWidgets, QtCore


class CharacterizeParamsFrame(QtWidgets.QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        vBoxCharacterizeParams1 = QtWidgets.QVBoxLayout()
        self.hBoxCharacterizeLayout1 = QtWidgets.QHBoxLayout()
        self.characterizeTargetLabel = QtWidgets.QLabel("Characterization Targets")
        characterizeResoLabel = QtWidgets.QLabel("Resolution")
        characterizeResoLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.characterizeResoEdit = QtWidgets.QLineEdit("3.0")
        characterizeISIGLabel = QtWidgets.QLabel("I/Sigma")
        characterizeISIGLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.characterizeISIGEdit = QtWidgets.QLineEdit("2.0")
        self.characterizeAnomCheckBox = QtWidgets.QCheckBox("Anomolous")
        self.characterizeAnomCheckBox.setChecked(False)
        self.hBoxCharacterizeLayout2 = QtWidgets.QHBoxLayout()
        characterizeCompletenessLabel = QtWidgets.QLabel("Completeness")
        characterizeCompletenessLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.characterizeCompletenessEdit = QtWidgets.QLineEdit("0.99")
        characterizeMultiplicityLabel = QtWidgets.QLabel("Multiplicity")
        characterizeMultiplicityLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.characterizeMultiplicityEdit = QtWidgets.QLineEdit("auto")
        characterizeDoseLimitLabel = QtWidgets.QLabel("Dose Limit")
        characterizeDoseLimitLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.characterizeDoseLimitEdit = QtWidgets.QLineEdit("100")
        characterizeSpaceGroupLabel = QtWidgets.QLabel("Space Group")
        characterizeSpaceGroupLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.characterizeSpaceGroupEdit = QtWidgets.QLineEdit("P1")
        self.hBoxCharacterizeLayout1.addWidget(characterizeResoLabel)
        self.hBoxCharacterizeLayout1.addWidget(self.characterizeResoEdit)
        self.hBoxCharacterizeLayout1.addWidget(characterizeISIGLabel)
        self.hBoxCharacterizeLayout1.addWidget(self.characterizeISIGEdit)
        self.hBoxCharacterizeLayout1.addWidget(characterizeSpaceGroupLabel)
        self.hBoxCharacterizeLayout1.addWidget(self.characterizeSpaceGroupEdit)
        self.hBoxCharacterizeLayout1.addWidget(self.characterizeAnomCheckBox)
        self.hBoxCharacterizeLayout2.addWidget(characterizeCompletenessLabel)
        self.hBoxCharacterizeLayout2.addWidget(self.characterizeCompletenessEdit)
        self.hBoxCharacterizeLayout2.addWidget(characterizeMultiplicityLabel)
        self.hBoxCharacterizeLayout2.addWidget(self.characterizeMultiplicityEdit)
        self.hBoxCharacterizeLayout2.addWidget(characterizeDoseLimitLabel)
        self.hBoxCharacterizeLayout2.addWidget(self.characterizeDoseLimitEdit)
        vBoxCharacterizeParams1.addWidget(self.characterizeTargetLabel)
        vBoxCharacterizeParams1.addLayout(self.hBoxCharacterizeLayout1)
        vBoxCharacterizeParams1.addLayout(self.hBoxCharacterizeLayout2)
        self.setLayout(vBoxCharacterizeParams1)

    def get_params(self):
        return {
            "aimed_completeness": float(self.characterizeCompletenessEdit.text()),
            "aimed_multiplicity": str(self.characterizeMultiplicityEdit.text()),
            "aimed_resolution": float(self.characterizeResoEdit.text()),
            "aimed_ISig": float(self.characterizeISIGEdit.text()),
        }
