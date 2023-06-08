from qtpy.QtCore import QThread, QTimer, QEventLoop, Signal, QPoint, Qt, QObject
from qtpy import QtGui
from PIL import Image, ImageQt
import os
import sys
import urllib
from io import BytesIO
import logging
from config_params import SERVER_CHECK_DELAY
import raddoseLib

logger = logging.getLogger()


class VideoThread(QThread):
    frame_ready = Signal(object)
    def camera_refresh(self):
        pixmap_orig = QtGui.QPixmap(320, 180)
        if self.url:
            try:
                file = BytesIO(urllib.request.urlopen(self.url, timeout=self.delay/1000).read())
                img = Image.open(file)
                qimage = ImageQt.ImageQt(img)
                pixmap_orig = QtGui.QPixmap.fromImage(qimage)
                self.showing_error = False
            except Exception as e:
                if not self.showing_error:
                    painter = QtGui.QPainter(pixmap_orig)
                    painter.setPen(QtGui.QPen(Qt.white))
                    painter.drawText( QPoint(10, 10), "No image obtained from: " )
                    painter.drawText( QPoint(10, 30), f"{self.url}")
                    painter.end()
                    self.frame_ready.emit(pixmap_orig)
                    self.showing_error = True

        if self.camera_object:
            retval,self.currentFrame = self.camera_object.read()
            if self.currentFrame is None:
                logger.debug('no frame read from stream URL - ensure the URL does not end with newline and that the filename is correct')
                return
            height,width=self.currentFrame.shape[:2]
            qimage= QtGui.QImage(self.currentFrame,width,height,3*width,QtGui.QImage.Format_RGB888)
            qimage = qimage.rgbSwapped()
            pixmap_orig = QtGui.QPixmap.fromImage(qimage)
            if self.width and self.height:
                pixmap_orig = pixmap_orig.scaled(self.width, self.height)
        
        if not self.showing_error:
            self.frame_ready.emit(pixmap_orig)
            
        
    def __init__(self, *args, delay=1000, url='', camera_object=None, width=None, height=None,**kwargs):
        self.delay = delay
        self.width = width
        self.height = height
        self.url = url
        self.camera_object = camera_object
        self.showing_error = False
        QThread.__init__(self, *args, **kwargs)
    
    def updateCam(self, camera_object):
        self.camera_object = camera_object
        
    def run(self):
        while True:
            self.camera_refresh()
            self.msleep(self.delay)


class RaddoseThread(QThread):
    lifetime = Signal(float)
    def __init__(self, *args, avg_dwd = 10, #Default of 10MGy 
                beamsizeV = 1.0, beamsizeH = 2.0,
                vectorL = 0.0,
                energy = 12.66,
                flux = -1.0,
                wedge = 180.0,
                verbose = False, **kwargs):
        self.avg_dwd = avg_dwd
        self.beamsizeV = beamsizeV
        self.beamsizeH = beamsizeH
        self.vectorL = vectorL
        self.energy = energy
        self.flux = flux
        self.wedge = wedge
        self.verbose = verbose
        QThread.__init__(self, *args, **kwargs)

    def run(self):
        lifetime_value = raddoseLib.fmx_expTime(self.avg_dwd, self.beamsizeV, self.beamsizeH, self.vectorL, self.energy, self.flux, self.wedge, self.verbose)
        self.lifetime.emit(lifetime_value)


class ServerCheckThread(QThread):
    def __init__(self, *args, delay=SERVER_CHECK_DELAY, **kwargs):
        self.delay = delay
        QThread.__init__(self, *args, **kwargs)

    def run(self):
        import db_lib
        beamline = os.environ["BEAMLINE_ID"]
        while True:
            if db_lib.getBeamlineConfigParam(beamline, "visitDirectory") != os.getcwd():
                message = "The server visit directory has changed, stopping!"
                logger.error(message)
                print(message)
                sys.exit(1)
            self.msleep(self.delay)
