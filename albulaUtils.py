try:
  import dectris.albula
except ImportError as e:
  print('albula library import error: %s' %e)
from functools import singledispatch
from time import sleep
global albulaFrame, albulaSubFrame, currentMasterH5
albulaFrame = None
albulaSubframeFrame = None
currentMasterH5 = None
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

# def albulaDispFile(filename):
#  global albulaFrame,albulaSubFrame
#
#  if (albulaFrame == None or albulaSubFrame == None):
#     albulaFrame = dectris.albula.openMainFrame()
#     albulaFrame.disableClose()
#     albulaSubFrame = albulaFrame.openSubFrame()
#  try:
#    albulaSubFrame.loadFile(filename)
#  except dectris.albula.DNoObject:
#    albulaFrame = dectris.albula.openMainFrame()
#    albulaSubFrame = albulaFrame.openSubFrame()
#    albulaSubFrame.loadFile(filename)


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

#@singledispatch
#def albulaDispFile(filename):
#    global albulaFrame,albulaSubFrame
#
#    if (albulaFrame == None or albulaSubFrame == None):
#        albulaFrame = dectris.albula.openMainFrame()
#        albulaFrame.disableClose()
#        albulaSubFrame = albulaFrame.openSubFrame()
#    try:
#        albulaSubFrame.loadFile(filename)
#    except dectris.albula.DNoObject:
#        albulaFrame = dectris.albula.openMainFrame()
#        albulaSubFrame = albulaFrame.openSubFrame()
#        albulaSubFrame.loadFile(filename)
    
#@albulaDispFile.register
def albulaDispFile(filename: tuple):
    global albulaFrame,albulaSubFrame,currentMasterH5

    if (albulaFrame == None or albulaSubFrame == None):
        albulaFrame = dectris.albula.openMainFrame()
        albulaFrame.disableClose()
        albulaSubFrame = albulaFrame.openSubFrame()

    try:
        if not (currentMasterH5 == filename[0]):
            albulaSubFrame.loadFile(filename[0])
            sleep(1)
            currentMasterH5 = filename[0]
        albulaSubFrame.goTo(filename[1])
    except dectris.albula.DNoObject:
        albulaFrame = dectris.albula.openMainFrame()
        albulaSubFrame = albulaFrame.openSubFrame()
        albulaSubFrame.loadFile(filename[0])
        albulaSubFrame.goTo(filename[1])

