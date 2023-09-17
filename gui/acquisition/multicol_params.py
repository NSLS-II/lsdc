from qtpy import QtWidgets, QtCore


class MultiColParamsFrame(QtWidgets.QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.hBoxMultiColParamsLayout1 = QtWidgets.QHBoxLayout()
        self.hBoxMultiColParamsLayout1.setAlignment(QtCore.Qt.AlignLeft)
        multiColCutoffLabel = QtWidgets.QLabel("Diffraction Cutoff")
        multiColCutoffLabel.setFixedWidth(110)
        self.multiColCutoffEdit = QtWidgets.QLineEdit(
            "320"
        )  # may need to store this in DB at some point, it's a silly number for now
        self.multiColCutoffEdit.setFixedWidth(60)
        self.hBoxMultiColParamsLayout1.addWidget(multiColCutoffLabel)
        self.hBoxMultiColParamsLayout1.addWidget(self.multiColCutoffEdit)
        self.setLayout(self.hBoxMultiColParamsLayout1)

