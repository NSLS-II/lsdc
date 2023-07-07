from qtpy import QtWidgets, QtCore
import daq_utils
from epics import PV
import typing

if typing.TYPE_CHECKING:
    from gui.control_main import ControlMain


class ZoomSlider(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self.slider.setMinimum(1)
        self.slider.setMaximum(4)
        self.slider.setValue(1)
        self.slider.setTickInterval(1)
        self.slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        self.slider.setSingleStep(1)
        self.slider.valueChanged.connect(self.zoomLevelToggledCB)

        self.centerMarkerCharOffsetX = 12
        self.centerMarkerCharOffsetY = 18
        self.lowMagCursorX_pv = PV(daq_utils.pvLookupDict["lowMagCursorX"])
        self.lowMagCursorY_pv = PV(daq_utils.pvLookupDict["lowMagCursorY"])
        self.highMagCursorX_pv = PV(daq_utils.pvLookupDict["highMagCursorX"])
        self.highMagCursorY_pv = PV(daq_utils.pvLookupDict["highMagCursorY"])

        labels = [f"Mag{i}" for i in range(1, 5)]

        if labels is not None:
            self.widget_layout = QtWidgets.QVBoxLayout(self)
            self.label_layout = QtWidgets.QHBoxLayout()
            self.widget_layout.addWidget(self.slider)
            self.widget_layout.addLayout(self.label_layout)
            for label in labels:
                label = QtWidgets.QLabel(str(label))
                self.label_layout.addWidget(
                    label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter
                )
        else:
            self.widget_layout = QtWidgets.QVBoxLayout(self)
            self.widget_layout.addWidget(self.slider)

        self.setLayout(self.widget_layout)

    def parent(self) -> ControlMain:
        return typing.cast("ControlMain", super().parent())

    def zoomLevelToggledCB(self, value):
        fov = {}
        zoomedCursorX = daq_utils.screenPixCenterX - self.centerMarkerCharOffsetX
        zoomedCursorY = daq_utils.screenPixCenterY - self.centerMarkerCharOffsetY
        if value == 1:
            capture = self.parent().captureLowMag
            fov["x"] = daq_utils.lowMagFOVx
            fov["y"] = daq_utils.lowMagFOVy
            cursor_x = (
                self.parent().lowMagCursorX_pv.get() - self.centerMarkerCharOffsetX
            )
            cursor_y = (
                self.parent().lowMagCursorY_pv.get() - self.centerMarkerCharOffsetY
            )
        elif value == 2:
            capture = self.parent().captureLowMagZoom
            fov["x"] = daq_utils.lowMagFOVx / 2.0
            fov["y"] = daq_utils.lowMagFOVy / 2.0
            cursor_x = zoomedCursorX
            cursor_y = zoomedCursorY
        elif value == 3:
            capture = self.parent().captureHighMag
            fov["x"] = daq_utils.highMagFOVx
            fov["y"] = daq_utils.highMagFOVy
            cursor_x = (
                self.parent().highMagCursorX_pv.get() - self.centerMarkerCharOffsetX
            )
            cursor_y = (
                self.parent().highMagCursorY_pv.get() - self.centerMarkerCharOffsetY
            )
        elif value == 4:
            capture = self.parent().captureHighMagZoom
            fov["x"] = daq_utils.highMagFOVx / 2.0
            fov["y"] = daq_utils.highMagFOVy / 2.0
            cursor_x = zoomedCursorX
            cursor_y = zoomedCursorY

        self.parent().flushBuffer(capture)
        self.parent().centerMarker.setPos(cursor_x, cursor_y)
        self.parent().adjustGraphics4ZoomChange(fov)
        self.parent().sampleZoomChangeSignal.emit(capture)
