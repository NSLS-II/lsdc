from qtpy import QtWidgets, QtGui, QtCore
import daq_utils

class VectorMarker(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, *args, **kwargs):
        brush = kwargs.pop('brush', QtGui.QBrush(QtCore.Qt.blue))
        pen = kwargs.pop('pen', QtGui.QPen(QtCore.Qt.blue))
        self.parent = kwargs.pop('parent', None)
        self.pointName = kwargs.pop('pointName', None)
        super().__init__(*args, **kwargs)
        self.setBrush(brush)
        self.setPen(pen)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsEllipseItem.ItemSendsGeometryChanges)
    
    
    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            if self.parent and self.parent.vecLine:
                self.parent.scene.removeItem(self.parent.vecLine)
                self.parent.drawVector()
        return super().itemChange(change, value)
    
    
    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        print("New position:", self.pos())
        if self.parent:
            micron_x = self.parent.screenXPixels2microns(self.pos().x())
            micron_y = self.parent.screenYPixels2microns(self.pos().y())
            if self.pointName and getattr(self.parent, self.pointName):
                omega = self.parent.omegaRBV_pv.get()
                point = getattr(self.parent, self.pointName)
                gonio_offset_x, gonio_offset_y, gonio_offset_z, omega = daq_utils.lab2gonio(micron_x, -micron_y, 0, omega)
                gonioCoords = {"x": self.parent.sampx_pv.get() + gonio_offset_x, 
                               "y": self.parent.sampy_pv.get() + gonio_offset_y, 
                               "z": self.parent.sampz_pv.get() + gonio_offset_z, 
                               "omega": omega}
                vectorCoords = self.parent.transform_vector_coords(
                                    point["coords"], gonioCoords
                                )
                point["coords"] = vectorCoords
                point["gonioCoords"] = gonioCoords

        return super().mouseReleaseEvent(event)