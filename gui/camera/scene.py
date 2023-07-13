from PyQt5.QtWidgets import QGraphicsSceneWheelEvent
from qtpy.QtWidgets import QGraphicsScene, QGraphicsSceneWheelEvent
from qtpy.QtCore import Signal

class CustomScene(QGraphicsScene):
    y_value = Signal(int)
    def wheelEvent(self, event: QGraphicsSceneWheelEvent) -> None:
        self.y_value.emit(event.delta())
        return super().wheelEvent(event)

        
