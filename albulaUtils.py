try:
  import dectris.albula
except ImportError as e:
  print('albula library import error: %s' %e)
import logging
logger = logging.getLogger(__name__)
logger.info('reading albulaUtils')
from functools import singledispatch
from time import sleep
global albulaFrame, albulaSubFrame, currentMasterH5
albulaFrame = None
albulaSubframeFrame = None
currentMasterH5 = None
imgSeries = None
global seriesDict
seriesDict = {}

def albulaClose(): #not used
  global albulaFrame,albulaSubFrame
  if (albulaSubFrame != None):
     albulaSubFrame.close()

  if (albulaFrame != None):
     albulaFrame.close()
  

def albulaDispImage(Dimage):
  global albulaFrame,albulaSubFrame

  if (albulaFrame == None or albulaSubFrame == None):
     albulaFrame = dectris.albula.openMainFrame()
     albulaFrame.disableClose()
     albulaSubFrame = albulaFrame.openSubFrame()
  try:
    albulaSubFrame.loadImage(Dimage)
  except dectris.albula.DNoObject:
    albulaFrame = dectris.albula.openMainFrame()
    albulaSubFrame = albulaFrame.openSubFrame()
    albulaSubFrame.loadImage(Dimage)

def albulaConv(filename,imgNum=1):

  series = dectris.albula.DImageSeries()
  series.open(filename)
  img = series[imgNum]
  dectris.albula.DImageWriter.write(img,"testOut.tif")


def albulaDispH5(filename,imgNum=1):
  if not (filename in seriesDict.keys()):
    seriesDict[filename] = dectris.albula.DImageSeries(filename)
  img = seriesDict[filename][imgNum]
  albulaDispImage(img)

@singledispatch
def albulaDispFile(filename):
    print(type(filename))
    raise Exception("type not supported, only str, list, or tuple")

@albulaDispFile.register(str)
def _albulaDispFile(filename):
    global albulaFrame,albulaSubFrame,currentMasterH5

    if (albulaFrame == None or albulaSubFrame == None):
        albulaFrame = dectris.albula.openMainFrame()
        albulaFrame.disableClose()
        albulaSubFrame = albulaFrame.openSubFrame()
    try:
        logger.info('loading file %s'% filename)
        albulaSubFrame.loadFile(filename)
        currentMasterH5 = ""
    except dectris.albula.DNoObject:
        albulaFrame = dectris.albula.openMainFrame()
        albulaSubFrame = albulaFrame.openSubFrame()
        albulaSubFrame.loadFile(filename)

@albulaDispFile.register(tuple)    
@albulaDispFile.register(list)
def _albulaDispFile(filename):
    global albulaFrame,albulaSubFrame,currentMasterH5,imgSeries

    if (albulaFrame == None or albulaSubFrame == None):
        logger.debug('starting up albula')
        albulaFrame = dectris.albula.openMainFrame()
        albulaFrame.disableClose()
        albulaSubFrame = albulaFrame.openSubFrame()

    try:
        if not (currentMasterH5 == filename[0]):
            logger.info('reading file: %s' % filename[0])
            albulaSubFrame.loadFile(filename[0])
            imgSeries = dectris.albula.DImageSeries(filename[0])
            currentMasterH5 = filename[0]
        logger.debug('reading image number %s' % filename[1])
        albulaSubFrame.loadImage(imgSeries[filename[1]])
    except dectris.albula.DNoObject:
        albulaFrame = dectris.albula.openMainFrame()
        albulaSubFrame = albulaFrame.openSubFrame()
        imgSeries = dectris.albula.DimageSeries(filename[0])
        albulaSubFrame.loadImage(imgSeries[filename[1]])
        currentMasterH5 = filename[0]

