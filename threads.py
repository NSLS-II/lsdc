from qtpy.QtCore import QThread, QTimer, QEventLoop, Signal
from qtpy import QtGui
from PIL import Image, ImageQt
import urllib
from io import BytesIO
import logging
        
logger = logging.getLogger()


class VideoThread(QThread):
    frame_ready = Signal(object)
    def camera_refresh(self):
        try:
            pixmap_orig = QtGui.QPixmap()
            if self.url:
                file = BytesIO(urllib.request.urlopen(self.url).read())
                img = Image.open(file)
                qimage = ImageQt.ImageQt(img)
                pixmap_orig = QtGui.QPixmap.fromImage(qimage)
            if self.camera_object:
                retval,self.currentFrame = self.camera_object.read()
                if self.currentFrame is None:
                    logger.debug('no frame read from stream URL - ensure the URL does not end with newline and that the filename is correct')
                    return
                height,width=self.currentFrame.shape[:2]
                qimage=QtGui.QImage(self.currentFrame,width,height,3*width,QtGui.QImage.Format_RGB888)
                qimage = qimage.rgbSwapped()
                pixmap_orig = QtGui.QPixmap.fromImage(qimage)
            self.frame_ready.emit(pixmap_orig)
        except Exception as e:
            logger.error(f'Exception during hutch cam handling: {e} URL: {self.url}')
        
    def __init__(self, *args, delay=1000, url='', camera_object=None, **kwargs,):
        self.delay = delay
        self.url = url
        self.camera_object = camera_object
        QThread.__init__(self, *args, **kwargs)
    
    def updateCam(self, camera_object):
        self.camera_object = camera_object
        
    def run(self):
        while True:
            self.camera_refresh()
            self.msleep(self.delay)