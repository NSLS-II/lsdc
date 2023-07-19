from qtpy.QtGui import QCursor
from qtpy.QtWidgets import QGraphicsView
from qtpy.QtCore import Signal, Qt
import daq_utils
import typing

if typing.TYPE_CHECKING:
    from gui.control_main import ControlMain


class CustomView(QGraphicsView):
    y_value = Signal(float)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent: ControlMain = kwargs['parent']
        self.control_pressed = False

    def wheelEvent(self, event) -> None:
        """Wheel event to manage zoom in/out of sample cam"""
        self.y_value.emit(event.angleDelta().y())
        return super().wheelEvent(event)

    def enterEvent(self, event):
        self.setFocus()  # set focus on mouse enter
        super().enterEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.control_pressed = True
            self.setCursor(QCursor(Qt.CrossCursor))


    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.control_pressed = False
            self.setCursor(QCursor(Qt.ArrowCursor))

    def mousePressEvent(self, event) -> None:
        if self.control_pressed and event.button() == Qt.LeftButton:
            self.center_on_click(event)
        return super().mousePressEvent(event)


    def center_on_click(self, event):
        # If C2C is not clicked and user is in control, then C2C
        if self.parent.vidActionC2CRadio.isChecked():
            return
        correctedC2C_x = daq_utils.screenPixCenterX + (
                event.pos().x() - (self.parent.centerMarker.x() + self.parent.centerMarkerCharOffsetX)
            )
        correctedC2C_y = daq_utils.screenPixCenterY + (
            event.pos().y() - (self.parent.centerMarker.y() + self.parent.centerMarkerCharOffsetY)
        )
        fov = self.parent.getCurrentFOV()
        current_viewangle = self.parent.zoomSlider.get_current_viewangle()
        comm_s = f'center_on_click({correctedC2C_x},{correctedC2C_y},{fov["x"]},{fov["y"]},source="screen",maglevel=0,viewangle={current_viewangle})'
        if self.parent.govStateMessagePV.get(as_string=True) == "state SA":
            self.parent.aux_send_to_server(comm_s)
