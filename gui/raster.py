import logging
import typing

from qtpy import QtCore, QtWidgets

import albulaUtils

if typing.TYPE_CHECKING:
    from lsdcGui import ControlMain

logger = logging.getLogger()


class RasterCell(QtWidgets.QGraphicsRectItem):
    def __init__(self, x, y, w, h, topParent):
        super(RasterCell, self).__init__(x, y, w, h, None)
        self.topParent = topParent


def isInCell(position, item):
    if item.contains(position):
        return True
    return False


class RasterGroup(QtWidgets.QGraphicsItemGroup):
    def __init__(self, parent: "ControlMain"):
        super(RasterGroup, self).__init__()
        self.parent = parent
        self.setAcceptHoverEvents(True)
        self.currentSelectedCell = None

    def mousePressEvent(self, e):
        for i in range(len(self.parent.rasterList)):
            if self.parent.rasterList[i] != None:
                if self.parent.rasterList[i]["graphicsItem"].isSelected():
                    logger.info("found selected raster")
                    self.parent.SelectedItemData = self.parent.rasterList[i]["uid"]
                    self.parent.treeChanged_pv.put(1)
        if self.parent.vidActionRasterExploreRadio.isChecked():
            for cell in self.childItems():
                if cell.contains(e.pos()):
                    if cell.data(0) != None:
                        if self.currentSelectedCell:
                            self.currentSelectedCell.setPen(self.parent.redPen)
                            self.currentSelectedCell.setZValue(0)
                        spotcount = cell.data(0)
                        filename = cell.data(1)
                        d_min = cell.data(2)
                        intensity = cell.data(3)
                        if self.parent.staffScreenDialog.albulaDispCheckBox.isChecked():
                            if filename != "empty":
                                logger.debug(
                                    f"filename to display: {filename} spotcount: {spotcount} dmin: {d_min} intensity: {intensity}"
                                )
                                albulaUtils.albulaDispFile(filename)
                        if not (self.parent.rasterExploreDialog.isVisible()):
                            self.parent.rasterExploreDialog.show()
                        self.parent.rasterExploreDialog.setSpotCount(spotcount)
                        self.parent.rasterExploreDialog.setTotalIntensity(intensity)
                        self.parent.rasterExploreDialog.setResolution(d_min)
                        groupList = self.childItems()
                        cell.setPen(self.parent.yellowPen)
                        cell.setZValue(1)
                        self.currentSelectedCell = cell
                        break
        else:
            super(RasterGroup, self).mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if e.buttons() == QtCore.Qt.LeftButton:
            pass
        if e.buttons() == QtCore.Qt.RightButton:
            pass

        super(RasterGroup, self).mouseMoveEvent(e)
        logger.debug(f"pos:{self.pos()} event:{e}")  # TODO: Add event description

    def mouseReleaseEvent(self, e):
        super(RasterGroup, self).mouseReleaseEvent(e)
        if e.button() == QtCore.Qt.LeftButton:
            pass
        if e.button() == QtCore.Qt.RightButton:
            pass

    def hoverMoveEvent(self, e):
        super(RasterGroup, self).hoverEnterEvent(e)
        for cell in self.childItems():
            if isInCell(e.scenePos(), cell):
                if cell.data(0) != None:
                    spotcount = cell.data(0)
                    d_min = cell.data(2)
                    intensity = cell.data(3)
                    if not (self.parent.rasterExploreDialog.isVisible()):
                        self.parent.rasterExploreDialog.show()
                    self.parent.rasterExploreDialog.setSpotCount(spotcount)
                    self.parent.rasterExploreDialog.setTotalIntensity(intensity)
                    self.parent.rasterExploreDialog.setResolution(d_min)
