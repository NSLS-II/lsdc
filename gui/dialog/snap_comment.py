from qtpy import QtWidgets


class SnapCommentDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle("Snapshot Comment")
        self.setModal(False)
        vBoxColParams1 = QtWidgets.QVBoxLayout()
        hBoxColParams1 = QtWidgets.QHBoxLayout()
        self.textEdit = QtWidgets.QPlainTextEdit()
        vBoxColParams1.addWidget(self.textEdit)
        self.ologCheckBox = QtWidgets.QCheckBox("Save to Olog")
        self.ologCheckBox.setChecked(False)
        vBoxColParams1.addWidget(self.ologCheckBox)
        commentButton = QtWidgets.QPushButton("Add Comment")
        commentButton.clicked.connect(self.commentCB)
        cancelButton = QtWidgets.QPushButton("Cancel")
        cancelButton.clicked.connect(self.cancelCB)

        hBoxColParams1.addWidget(commentButton)
        hBoxColParams1.addWidget(cancelButton)
        vBoxColParams1.addLayout(hBoxColParams1)
        self.setLayout(vBoxColParams1)

    def cancelCB(self):
        self.comment = ""
        self.useOlog = False
        self.reject()

    def commentCB(self):
        self.comment = self.textEdit.toPlainText()
        self.useOlog = self.ologCheckBox.isChecked()
        self.accept()

    @staticmethod
    def getComment(parent=None):
        dialog = SnapCommentDialog(parent)
        result = dialog.exec_()
        return (dialog.comment, dialog.useOlog, result == QtWidgets.QDialog.Accepted)
