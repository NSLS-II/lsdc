from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt
import db_lib, daq_utils
import functools
from config_params import PUCKS_PER_DEWAR_SECTOR, DEWAR_SECTORS, SAMPLE_TIMER_DELAY
import logging
import typing
from typing import Optional

if typing.TYPE_CHECKING:
    from lsdcGui import ControlMain

logger = logging.getLogger()

global sampleNameDict
sampleNameDict = {}

global containerDict
containerDict = {}


class DewarTree(QtWidgets.QTreeView):
    def __init__(self, parent: "ControlMain"):
        super(DewarTree, self).__init__(parent)
        self.pucksPerDewarSector = PUCKS_PER_DEWAR_SECTOR[daq_utils.beamline]
        self.dewarSectors = DEWAR_SECTORS[daq_utils.beamline]
        self.parent = parent
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setAnimated(True)
        # self.model = QtGui.QStandardItemModel()
        self.model.itemChanged.connect(self.queueSelectedSample)
        # self.isExpanded = 1
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.openMenu)

    def openMenu(self, position):
        indexes = self.selectedIndexes()
        selectedLevels = set()
        if indexes:
            for index in indexes:
                level = 0
                while index.parent().isValid():
                    index = index.parent()
                    level += 1
                selectedLevels.add(level)
            if len(selectedLevels) == 1:
                level = list(selectedLevels)[0]
                menu = QtWidgets.QMenu()
                if level == 2:  # This is usually a request
                    deleteReqAction = QtWidgets.QAction(
                        "Delete selected request(s)", self
                    )
                    deleteReqAction.triggered.connect(self.deleteSelectedCB)
                    cloneReqAction = QtWidgets.QAction("Clone selected request", self)
                    cloneReqAction.triggered.connect(self.cloneRequestCB)
                    queueSelAction = QtWidgets.QAction(
                        "Queue selected request(s)", self
                    )
                    queueSelAction.triggered.connect(self.queueAllSelectedCB)
                    dequeueSelAction = QtWidgets.QAction(
                        "Dequeue selected request(s)", self
                    )
                    dequeueSelAction.triggered.connect(self.deQueueAllSelectedCB)
                    menu.addAction(cloneReqAction)
                    menu.addAction(queueSelAction)
                    menu.addAction(dequeueSelAction)
                    menu.addSeparator()
                    menu.addAction(deleteReqAction)
                menu.exec_(self.viewport().mapToGlobal(position))

    def cloneRequestCB(self):
        # Only the first selected request is cloned (If multiple are chosen)
        index = self.selectedIndexes()[0]
        item = self.model.itemFromIndex(index)
        requestData = db_lib.getRequestByID(item.data(32))
        protocol = requestData["request_obj"]["protocol"]
        if "raster" in protocol.lower():  # Will cover specRaster and stepRaster as well
            self.parent.cloneRequestCB()
        elif "standard" in protocol.lower():
            self.parent.addRequestsToAllSelectedCB()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.deleteSelectedCB(0)
        else:
            super(DewarTree, self).keyPressEvent(event)

    def refreshTree(self):
        self.parent.dewarViewToggleCheckCB()

    def refreshTreeDewarView(self):
        selectedIndex = None
        mountedIndex = None
        selectedSampleIndex = None
        puck = ""
        collectionRunning = False
        self.model.clear()
        dewarContents = db_lib.getContainerByName(
            daq_utils.primaryDewarName, daq_utils.beamline
        )["content"]
        for i in range(0, len(dewarContents)):  # dewar contents is the list of puck IDs
            parentItem = self.model.invisibleRootItem()
            if dewarContents[i] == "":
                puck = ""
                puckName = ""
            else:
                if dewarContents[i] not in containerDict:
                    puck = db_lib.getContainerByID(dewarContents[i])
                    containerDict[dewarContents[i]] = puck
                else:
                    puck = containerDict[dewarContents[i]]
                puckName = puck["name"]
            index_s = "%d%s" % (
                (i) / self.pucksPerDewarSector + 1,
                chr(((i) % self.pucksPerDewarSector) + ord("A")),
            )
            item = QtGui.QStandardItem(
                QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"),
                index_s + " " + puckName,
            )
            item.setData(puckName, 32)
            item.setData("container", 33)
            parentItem.appendRow(item)
            parentItem = item
            if puck != "" and puckName != "private":
                puckContents = puck["content"]
                puckSize = len(puckContents)
                for j in range(0, len(puckContents)):  # should be the list of samples
                    if puckContents[j] != "":
                        if puckContents[j] not in sampleNameDict:
                            sampleName = db_lib.getSampleNamebyID(puckContents[j])
                            sampleNameDict[puckContents[j]] = sampleName
                        else:
                            sampleName = sampleNameDict[puckContents[j]]
                        position_s = str(j + 1) + "-" + sampleName
                        item = QtGui.QStandardItem(
                            QtGui.QIcon(
                                ":/trolltech/styles/commonstyle/images/file-16.png"
                            ),
                            position_s,
                        )
                        item.setData(
                            puckContents[j], 32
                        )  # just stuck sampleID there, but negate it to diff from reqID
                        item.setData("sample", 33)
                        if puckContents[j] == self.parent.mountedPin_pv.get():
                            item.setForeground(QtGui.QColor("red"))
                            font = QtGui.QFont()
                            font.setItalic(True)
                            font.setOverline(True)
                            font.setUnderline(True)
                            item.setFont(font)
                        parentItem.appendRow(item)
                        if puckContents[j] == self.parent.mountedPin_pv.get():
                            mountedIndex = self.model.indexFromItem(item)
                        if (
                            puckContents[j] == self.parent.selectedSampleID
                        ):  # looking for the selected item
                            logger.info("found " + str(self.parent.SelectedItemData))
                            selectedSampleIndex = self.model.indexFromItem(item)
                        sampleRequestList = db_lib.getRequestsBySampleID(
                            puckContents[j]
                        )
                        for k in range(len(sampleRequestList)):
                            if not ("protocol" in sampleRequestList[k]["request_obj"]):
                                continue
                            col_item = QtGui.QStandardItem(
                                QtGui.QIcon(
                                    ":/trolltech/styles/commonstyle/images/file-16.png"
                                ),
                                sampleRequestList[k]["request_obj"]["file_prefix"]
                                + "_"
                                + sampleRequestList[k]["request_obj"]["protocol"],
                            )
                            col_item.setData(sampleRequestList[k]["uid"], 32)
                            col_item.setData("request", 33)
                            col_item.setFlags(
                                Qt.ItemIsUserCheckable
                                | Qt.ItemIsEnabled
                                | Qt.ItemIsEditable
                                | Qt.ItemIsSelectable
                            )
                            if sampleRequestList[k]["priority"] == 99999:
                                col_item.setCheckState(Qt.Checked)
                                col_item.setBackground(QtGui.QColor("green"))
                                selectedIndex = self.model.indexFromItem(
                                    col_item
                                )  ##attempt to leave it on the request after collection

                                collectionRunning = True
                                self.parent.refreshCollectionParams(
                                    sampleRequestList[k], validate_hdf5=False
                                )
                            elif sampleRequestList[k]["priority"] > 0:
                                col_item.setCheckState(Qt.Checked)
                                col_item.setBackground(QtGui.QColor("white"))
                            elif sampleRequestList[k]["priority"] < 0:
                                col_item.setCheckable(False)
                                col_item.setBackground(QtGui.QColor("cyan"))
                            else:
                                col_item.setCheckState(Qt.Unchecked)
                                col_item.setBackground(QtGui.QColor("white"))
                            item.appendRow(col_item)
                            if (
                                sampleRequestList[k]["uid"]
                                == self.parent.SelectedItemData
                            ):  # looking for the selected item, this is a request
                                selectedIndex = self.model.indexFromItem(col_item)
                    else:  # this is an empty spot, no sample
                        position_s = str(j + 1)
                        item = QtGui.QStandardItem(
                            QtGui.QIcon(
                                ":/trolltech/styles/commonstyle/images/file-16.png"
                            ),
                            position_s,
                        )
                        item.setData("", 32)
                        parentItem.appendRow(item)
        # self.setModel(self.model)
        if selectedSampleIndex != None and collectionRunning == False:
            self.setCurrentIndex(selectedSampleIndex)
            if mountedIndex != None:
                self.model.itemFromIndex(mountedIndex).setForeground(
                    QtGui.QColor("red")
                )
                font = QtGui.QFont()
                font.setUnderline(True)
                font.setItalic(True)
                font.setOverline(True)
                self.model.itemFromIndex(mountedIndex).setFont(font)
            self.parent.row_clicked(selectedSampleIndex)
        elif selectedSampleIndex == None and collectionRunning == False:
            if mountedIndex != None:
                self.setCurrentIndex(mountedIndex)
                self.model.itemFromIndex(mountedIndex).setForeground(
                    QtGui.QColor("red")
                )
                font = QtGui.QFont()
                font.setUnderline(True)
                font.setItalic(True)
                font.setOverline(True)
                self.model.itemFromIndex(mountedIndex).setFont(font)
                self.parent.row_clicked(mountedIndex)
        else:
            pass
        if selectedIndex != None and collectionRunning == False:
            self.setCurrentIndex(selectedIndex)
            self.parent.row_clicked(selectedIndex)
        if collectionRunning == True:
            if mountedIndex != None:
                self.setCurrentIndex(mountedIndex)
        if self.isExpanded:
            self.expandAll()
        else:
            self.collapseAll()
        self.scrollTo(self.currentIndex(), QtWidgets.QAbstractItemView.PositionAtCenter)

    def refreshTreePriorityView(
        self,
    ):  # "item" is a sample, "col_items" are requests which are children of samples.
        collectionRunning = False
        selectedIndex = None
        mountedIndex = None
        selectedSampleIndex = None
        self.model.clear()
        self.orderedRequests = db_lib.getOrderedRequestList(daq_utils.beamline)
        dewarContents = db_lib.getContainerByName(
            daq_utils.primaryDewarName, daq_utils.beamline
        )["content"]
        maxPucks = len(dewarContents)
        requestedSampleList = []
        mountedPin = self.parent.mountedPin_pv.get()
        for i in range(
            len(self.orderedRequests)
        ):  # I need a list of samples for parent nodes
            if self.orderedRequests[i]["sample"] not in requestedSampleList:
                requestedSampleList.append(self.orderedRequests[i]["sample"])
        for i in range(len(requestedSampleList)):
            sample = db_lib.getSampleByID(requestedSampleList[i])
            owner = sample["owner"]
            parentItem = self.model.invisibleRootItem()
            nodeString = str(db_lib.getSampleNamebyID(requestedSampleList[i]))
            item = QtGui.QStandardItem(
                QtGui.QIcon(":/trolltech/styles/commonstyle/images/file-16.png"),
                nodeString,
            )
            item.setData(requestedSampleList[i], 32)
            item.setData("sample", 33)
            if requestedSampleList[i] == mountedPin:
                item.setForeground(QtGui.QColor("red"))
                font = QtGui.QFont()
                font.setItalic(True)
                font.setOverline(True)
                font.setUnderline(True)
                item.setFont(font)
            parentItem.appendRow(item)
            if requestedSampleList[i] == mountedPin:
                mountedIndex = self.model.indexFromItem(item)
            if (
                requestedSampleList[i] == self.parent.selectedSampleID
            ):  # looking for the selected item
                selectedSampleIndex = self.model.indexFromItem(item)
            parentItem = item
            for k in range(len(self.orderedRequests)):
                if self.orderedRequests[k]["sample"] == requestedSampleList[i]:
                    col_item = QtGui.QStandardItem(
                        QtGui.QIcon(
                            ":/trolltech/styles/commonstyle/images/file-16.png"
                        ),
                        self.orderedRequests[k]["request_obj"]["file_prefix"]
                        + "_"
                        + self.orderedRequests[k]["request_obj"]["protocol"],
                    )
                    col_item.setData(self.orderedRequests[k]["uid"], 32)
                    col_item.setData("request", 33)
                    col_item.setFlags(
                        Qt.ItemIsUserCheckable
                        | Qt.ItemIsEnabled
                        | Qt.ItemIsEditable
                        | Qt.ItemIsSelectable
                    )
                    if self.orderedRequests[k]["priority"] == 99999:
                        col_item.setCheckState(Qt.Checked)
                        col_item.setBackground(QtGui.QColor("green"))
                        collectionRunning = True
                        self.parent.refreshCollectionParams(
                            self.orderedRequests[k], validate_hdf5=False
                        )

                    elif self.orderedRequests[k]["priority"] > 0:
                        col_item.setCheckState(Qt.Checked)
                        col_item.setBackground(QtGui.QColor("white"))
                    elif self.orderedRequests[k]["priority"] < 0:
                        col_item.setCheckable(False)
                        col_item.setBackground(QtGui.QColor("cyan"))
                    else:
                        col_item.setCheckState(Qt.Unchecked)
                        col_item.setBackground(QtGui.QColor("white"))
                    item.appendRow(col_item)
                    if (
                        self.orderedRequests[k]["uid"] == self.parent.SelectedItemData
                    ):  # looking for the selected item
                        selectedIndex = self.model.indexFromItem(col_item)
        # self.setModel(self.model)
        if selectedSampleIndex != None and collectionRunning == False:
            self.setCurrentIndex(selectedSampleIndex)
            self.parent.row_clicked(selectedSampleIndex)
        elif selectedSampleIndex == None and collectionRunning == False:
            if mountedIndex != None:
                self.setCurrentIndex(mountedIndex)
                self.parent.row_clicked(mountedIndex)
        else:
            pass

        if selectedIndex != None and collectionRunning == False:
            self.setCurrentIndex(selectedIndex)
            self.parent.row_clicked(selectedIndex)
        self.scrollTo(self.currentIndex(), QtWidgets.QAbstractItemView.PositionAtCenter)
        self.expandAll()

    def queueSelectedSample(self, item):
        reqID = str(item.data(32))
        checkedSampleRequest = db_lib.getRequestByID(reqID)  # line not needed???
        if item.checkState() == Qt.Checked:
            db_lib.updatePriority(reqID, 5000)
        else:
            db_lib.updatePriority(reqID, 0)
        item.setBackground(QtGui.QColor("white"))
        self.parent.treeChanged_pv.put(
            self.parent.processID
        )  # the idea is touch the pv, but have this gui instance not refresh

    def queueAllSelectedCB(self):
        selmod = self.selectionModel()
        selection = selmod.selection()
        indexes = selection.indexes()
        for i in range(len(indexes)):
            item = self.model.itemFromIndex(indexes[i])
            itemData = str(item.data(32))
            itemDataType = str(item.data(33))
            if (itemDataType == "request") and item.isCheckable():
                selectedSampleRequest = db_lib.getRequestByID(itemData)
                db_lib.updatePriority(itemData, 5000)
        self.parent.treeChanged_pv.put(1)

    def deQueueAllSelectedCB(self):
        selmod = self.selectionModel()
        selection = selmod.selection()
        indexes = selection.indexes()
        for i in range(len(indexes)):
            item = self.model.itemFromIndex(indexes[i])
            itemData = str(item.data(32))
            itemDataType = str(item.data(33))
            if (itemDataType == "request") and item.isCheckable():
                selectedSampleRequest = db_lib.getRequestByID(itemData)
                db_lib.updatePriority(itemData, 0)
        self.parent.treeChanged_pv.put(1)

    def confirmDelete(self, numReq):
        if numReq:
            quit_msg = f"Are you sure you want to delete {numReq} requests?"
        else:
            quit_msg = "Are you sure you want to delete all requests?"
        self.parent.timerSample.stop()
        reply = QtWidgets.QMessageBox.question(
            self,
            "Message",
            quit_msg,
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No,
        )
        self.parent.timerSample.start(SAMPLE_TIMER_DELAY)
        if reply == QtWidgets.QMessageBox.Yes:
            return 1
        else:
            return 0

    def deleteSelectedCB(self, deleteAll):
        if deleteAll:
            if not self.confirmDelete(0):
                return
            self.selectAll()
        selmod = self.selectionModel()
        selection = selmod.selection()
        indexes = selection.indexes()
        if len(indexes) > 1:
            if not self.confirmDelete(len(indexes)):
                return
        progressInc = 100.0 / float(len(indexes))
        self.parent.progressDialog.setWindowTitle("Deleting Requests")
        self.parent.progressDialog.show()
        for i in range(len(indexes)):
            self.parent.progressDialog.setValue(int((i + 1) * progressInc))
            item = self.model.itemFromIndex(indexes[i])
            itemData = str(item.data(32))
            itemDataType = str(item.data(33))
            if itemDataType == "request":
                selectedSampleRequest = db_lib.getRequestByID(itemData)
                self.selectedSampleID = selectedSampleRequest["sample"]
                db_lib.deleteRequest(selectedSampleRequest["uid"])
                if selectedSampleRequest["request_obj"]["protocol"] in (
                    "raster",
                    "stepRaster",
                    "multiCol",
                ):
                    for i in range(len(self.parent.rasterList)):
                        if self.parent.rasterList[i] != None:
                            if (
                                self.parent.rasterList[i]["uid"]
                                == selectedSampleRequest["uid"]
                            ):
                                self.parent.scene.removeItem(
                                    self.parent.rasterList[i]["graphicsItem"]
                                )
                                self.parent.rasterList[i] = None
                if (
                    selectedSampleRequest["request_obj"]["protocol"] == "vector"
                    or selectedSampleRequest["request_obj"]["protocol"] == "stepVector"
                ):
                    self.parent.clearVectorCB()
        self.parent.progressDialog.close()
        self.parent.treeChanged_pv.put(1)

    def expandAllCB(self):
        self.expandAll()

    def collapseAllCB(self):
        self.collapseAll()

    def getSelectedSample(self):
        selectedSampleID = None
        if self.selectedIndexes():
            index = self.selectedIndexes()[0]
            item = self.model.itemFromIndex(index)
            if str(item.data(33)) == "sample":
                selectedSampleID = str(item.data(32))
            elif str(item.data(33)) == "request":
                selectedSampleRequest = db_lib.getRequestByID(item.data(32))
                selectedSampleID = selectedSampleRequest["sample"]
        return selectedSampleID
