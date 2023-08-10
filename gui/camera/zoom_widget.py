from qtpy import QtWidgets, QtCore, QtGui
import daq_utils
from epics import PV
import typing

if typing.TYPE_CHECKING:
    from gui.control_main import ControlMain

class ClickableQSlider(QtWidgets.QSlider):
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            value = self.minimum() + ((self.maximum() - self.minimum()) * event.x()) / self.width()
            self.setValue(round(value))
            event.accept()
        else:
            super().mousePressEvent(event)


class ZoomSlider(QtWidgets.QWidget):
    # Based on the stackoverflow answer: https://stackoverflow.com/a/54819051
    def __init__(self, config,
                 orientation=QtCore.Qt.Horizontal,
                 parent=None):
        super(ZoomSlider, self).__init__(parent=parent)
        self.parent: "ControlMain" = parent

        self.config = config
        self.zoom_levels = len(self.config)
        minimum = 1
        interval = 1
        maximum = self.zoom_levels
        levels = range(minimum, maximum+1)
        
        self.scaling_factor = [1, 2, 4, 6]
        
        labels = [f'Mag{i}' for i in levels]
        if labels is not None:
            if not isinstance(labels, (tuple, list)):
                raise Exception("<labels> is a list or tuple.")
            if len(labels) != len(levels):
                raise Exception("Size of <labels> doesn't match levels.")
            self.levels=list(zip(levels,labels))
        else:
            self.levels=list(zip(levels,map(str,levels)))

        if orientation==QtCore.Qt.Horizontal:
            self.layout=QtWidgets.QVBoxLayout(self)
        elif orientation==QtCore.Qt.Vertical:
            self.layout=QtWidgets.QHBoxLayout(self)
        else:
            raise Exception("<orientation> wrong.")

        # gives some space to print labels
        self.left_margin=10
        self.top_margin=10
        self.right_margin=10
        self.bottom_margin=10

        self.layout.setContentsMargins(self.left_margin,self.top_margin,
                self.right_margin,self.bottom_margin)

        self.slider=ClickableQSlider(orientation, self)
        self.slider.setMinimum(minimum)
        self.slider.setMaximum(maximum)
        self.slider.setValue(minimum)
        if orientation==QtCore.Qt.Horizontal:
            self.slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
            self.slider.setMinimumWidth(200) # just to make it easier to read
        else:
            self.slider.setTickPosition(QtWidgets.QSlider.TicksLeft)
            self.slider.setMinimumHeight(300) # just to make it easier to read
        self.slider.setTickInterval(interval)
        self.slider.setSingleStep(1)

        self.layout.addWidget(self.slider)

        self.slider.valueChanged.connect(self.zoom_level_toggled)

        self.centerMarkerCharOffsetX = 12
        self.centerMarkerCharOffsetY = 18
        self.lowMagCursorX_pv = PV(daq_utils.pvLookupDict["lowMagCursorX"])
        self.lowMagCursorY_pv = PV(daq_utils.pvLookupDict["lowMagCursorY"])
        self.highMagCursorX_pv = PV(daq_utils.pvLookupDict["highMagCursorX"])
        self.highMagCursorY_pv = PV(daq_utils.pvLookupDict["highMagCursorY"])

        

    def paintEvent(self, e):

        super(ZoomSlider,self).paintEvent(e)

        style=self.slider.style()
        painter=QtGui.QPainter(self)
        st_slider=QtWidgets.QStyleOptionSlider()
        st_slider.initFrom(self.slider)
        st_slider.orientation=self.slider.orientation()

        length=style.pixelMetric(QtWidgets.QStyle.PM_SliderLength, st_slider, self.slider)
        available=style.pixelMetric(QtWidgets.QStyle.PM_SliderSpaceAvailable, st_slider, self.slider)

        for v, v_str in self.levels:

            # get the size of the label
            rect=painter.drawText(QtCore.QRect(), QtCore.Qt.TextDontPrint, v_str)

            if self.slider.orientation()==QtCore.Qt.Horizontal:
                # I assume the offset is half the length of slider, therefore
                # + length//2
                x_loc=QtWidgets.QStyle.sliderPositionFromValue(self.slider.minimum(),
                        self.slider.maximum(), v, available)+length//2

                # left bound of the text = center - half of text width + L_margin
                left=x_loc-rect.width()//2+self.left_margin
                bottom=self.rect().bottom()-3

                # enlarge margins if clipping
                if v==self.slider.minimum():
                    if left<=0:
                        self.left_margin=rect.width()//2-x_loc
                    if self.bottom_margin<=rect.height():
                        self.bottom_margin=rect.height()

                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

                if v==self.slider.maximum() and rect.width()//2>=self.right_margin:
                    self.right_margin=rect.width()//2
                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

            else:
                y_loc=QtWidgets.QStyle.sliderPositionFromValue(self.slider.minimum(),
                        self.slider.maximum(), v, available, upsideDown=True)

                bottom=y_loc+length//2+rect.height()//2+self.top_margin-3
                # there is a 3 px offset that I can't attribute to any metric

                left=self.left_margin-rect.width()
                if left<=0:
                    self.left_margin=rect.width()+2
                    self.layout.setContentsMargins(self.left_margin,
                            self.top_margin, self.right_margin,
                            self.bottom_margin)

            pos= QtCore.QPointF(left, bottom)
            painter.drawText(pos, v_str)

        return
    

    def zoom_level_toggled(self, value=None):
        if value is None:
            value = self.slider.value()
        fov = {}
        zoomedCursorX = daq_utils.screenPixCenterX - self.centerMarkerCharOffsetX
        zoomedCursorY = daq_utils.screenPixCenterY - self.centerMarkerCharOffsetY
        camera_config = daq_utils.sampleCameraConfig[value - 1]

        if self.parent.capture.isOpened():
            self.parent.capture.release()
        
        self.parent.capture.open(camera_config["url"])
        fov['x'] = camera_config["fov"]["width"]
        fov['y'] = camera_config["fov"]["height"]

        if value == 1:
            cursor_x = (
                self.parent.lowMagCursorX_pv.get() - self.centerMarkerCharOffsetX
            )
            cursor_y = (
                self.parent.lowMagCursorY_pv.get() - self.centerMarkerCharOffsetY
            )
        elif value == 2:
            cursor_x = zoomedCursorX
            cursor_y = zoomedCursorY
        elif value == 3:
            cursor_x = (
                self.parent.highMagCursorX_pv.get() - self.centerMarkerCharOffsetX
            )
            cursor_y = (
                self.parent.highMagCursorY_pv.get() - self.centerMarkerCharOffsetY
            )
        elif value == 4:
            cursor_x = zoomedCursorX
            cursor_y = zoomedCursorY
        else:
            cursor_x = zoomedCursorX
            cursor_y = zoomedCursorY

        self.parent.centerMarker.setPos(cursor_x, cursor_y)
        self.parent.adjustGraphics4ZoomChange(fov, )


    def getFOV(self):
        fov = {"x": 0.0, "y": 0.0}
        config_fov = daq_utils.sampleCameraConfig[self.slider.value()-1]["fov"]
        fov["x"], fov["y"] = config_fov["width"], config_fov["height"]
        return fov
    
    def get_current_viewangle(self):
        current_viewangle = daq_utils.mag1ViewAngle
        if self.slider.value() == 2:
            current_viewangle = daq_utils.mag2ViewAngle
        elif self.slider.value() == 3:
            current_viewangle = daq_utils.mag3ViewAngle
        elif self.slider.value() == 4:
            current_viewangle = daq_utils.mag4ViewAngle
        
        return current_viewangle
    
    def get_zoom_mag(self):
        if self.slider.value() == 2:
            zoom, mag = 1, 'low'
        elif self.slider.value() == 3:
            zoom, mag = 0, 'high'
        elif self.slider.value() == 4:
            zoom, mag = 1, 'high'
        else:
            zoom, mag = 0, 'low'

        return zoom, mag
    
    def handle_wheel(self, value):
        slider_val = self.slider.value()
        if value > 0 and slider_val < self.slider.maximum():
            self.slider.setValue(slider_val+1)
        elif value < 0 and slider_val > self.slider.minimum():
            self.slider.setValue(slider_val-1)

    def get_scale(self):
        no_zoom_fov = daq_utils.sampleCameraConfig[0]["fov"]
        current_zoom_fov = daq_utils.sampleCameraConfig[self.slider.value()-1]["fov"]
        return no_zoom_fov['width']/current_zoom_fov['width']