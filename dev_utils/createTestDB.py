
import time
import os

import sys

import traceback

from mongoengine import NotUniqueError

from db_lib import *  # makes db connection

import config_params

primary_dewar_name = 'primaryDewarJohn'
beamline = "nyx"
owner = 'mike'

def createTestDB():
        createBeamline(beamline, "19id2")


        # containers
        createContainer(primary_dewar_name, 16, owner, kind='automounterDewar')  # All dewars currently in use are automounterDewar

        for i in range(1,5):  # 1 indexed, discontinuity for testing
            containerName = 'Puck_{0}'.format(i)
            createContainer(containerName, 16, owner, kind='16_pin_puck')


        for i in range(1,5):  # discontinuity for testing
            containerName = 'Puck_{0}'.format(i)
            insertIntoContainer(primary_dewar_name, owner, i, getContainerIDbyName(containerName, 'john'))

        # samples
        type_name = 'pin'
        for i in range(1,4):  # discontinuity for testing
            containerName = 'Puck_{0}'.format(i)
            for j in range(1,5):
                sampleName = 'samp_{0}_{1}'.format(i, j)

                try:
                    sampID = createSample(sampleName, owner, kind='16_puck_robot_dewar', sample_type=type_name)

                except NotUniqueError:
                    raise NotUniqueError('{0}'.format(sampleName))

                if not insertIntoContainer(containerName, owner, j, sampID):
                    print('name {0}, pos {1}, sampid {2}'.format(containerName, j, sampID))

def addBeamlineInfo():
        beamlineInfo(beamline, 'mountedSample', {'puckPos': 0, 'pinPos': 0, 'sampleID': '-99'})
        beamlineInfo(beamline, 'rasterScoreFlag',{'index':0} )

def addCommParams():
        setBeamlineConfigParam(beamline, 'beamlineComm', 'XF:19ID2-ES:NYX{Comm}')

def addCameraParams():
        setBeamlineConfigParam(beamline, 'has_xtalview', '1')
        setBeamlineConfigParam(beamline, 'xtal_url', 'http://xf17id1c-ioc2.cs.nsls2.local:8007/C2.MJPG.jpg')
        setBeamlineConfigParam(beamline, 'xtal_url_small', 'http://xf17id1c-ioc2.cs.nsls2.local:8008/C2.MJPG.jpg')
        setBeamlineConfigParam(beamline, 'camera_offset', '0.0')
        setBeamlineConfigParam(beamline, 'hutchTopCamURL','http://xf19id2-webcam2/axis-cgi/jpg/image.cgi?resolution=320x180&.jpg')
        setBeamlineConfigParam(beamline, 'hutchCornerCamURL','http://xf19id2-webcam1/axis-cgi/jpg/image.cgi?resolution=320x180&.jpg')
        setBeamlineConfigParam(beamline, 'lowMagCamURL', 'http://xf19id2-ioc2-1923.nsls2.bnl.local:8006/C2.MJPG.mjpg')
        setBeamlineConfigParam(beamline, 'highMagCamURL', 'http://xf19id2-ioc2-1923.nsls2.bnl.local:8005/C2.MJPG.mjpg')
	# Zoom URLs are currently the same, but will over-move when used for C2C, need the ROIs here
        setBeamlineConfigParam(beamline, 'highMagZoomCamURL', 'http://xf19id2-ioc2-1923.nsls2.bnl.local:8005/C2.MJPG.mjpg')
        setBeamlineConfigParam(beamline, 'lowMagZoomCamURL', 'http://xf19id2-ioc2-1923.nsls2.bnl.local:8006/C2.MJPG.mjpg')
        setBeamlineConfigParam(beamline, 'lowMagFOVx', '638')
        setBeamlineConfigParam(beamline, 'lowMagFOVy', '401')
        setBeamlineConfigParam(beamline, 'highMagFOVx', '210')
        setBeamlineConfigParam(beamline, 'highMagFOVy', '173')
        setBeamlineConfigParam(beamline, 'lowMagPixX', '640')
        setBeamlineConfigParam(beamline, 'lowMagPixY', '512')
        setBeamlineConfigParam(beamline, 'highMagPixX', '640')
        setBeamlineConfigParam(beamline, 'highMagPixY', '512')
        setBeamlineConfigParam(beamline, 'screenPixX', '640')
        setBeamlineConfigParam(beamline, 'screenPixY', '512')

def addHardwareParams():
        #dewarPlateName parameter is no longer used and has been removed
        setBeamlineConfigParam(beamline, 'dewarPlateMap', {'0':[180,-180], '1':[135,225], '2':[90,-270], '3':[45,-315], '4':[0,360], '5':[315,-45], '6':[270,90], '7':[225,-135]})

        setBeamlineConfigParam(beamline, 'gonioPvPrefix', 'XF:19IDC-ES:FMX')
        setBeamlineConfigParam(beamline, 'detector_id', 'EIGER-16')
        setBeamlineConfigParam(beamline, 'detRadius', '116.0')
        setBeamlineConfigParam(beamline, 'detector_type', 'pixel_array')
        setBeamlineConfigParam(beamline, 'has_edna', '1')
        setBeamlineConfigParam(beamline, 'has_beamline', '0')
        setBeamlineConfigParam(beamline, 'detector_offline', '0')
        setBeamlineConfigParam(beamline, 'mono_mot_code', 'mon')
        #hopefully unused, look to remove
        setBeamlineConfigParam(beamline, 'imgsrv_port', '14007')
        setBeamlineConfigParam(beamline, 'imgsrv_host', 'x25-h.nsls.bnl.gov')

        #don't forget to add these back to main dev_utils
        setBeamlineConfigParam(beamline, 'primaryDewarName', primary_dewar_name)        

        # below are all parameters that allow clean running of the LSDC GUI and server but
        # are not required for the GUI and server to start up.

        setBeamlineConfigParam(beamline, config_params.DETECTOR_OBJECT_TYPE, config_params.DETECTOR_OBJECT_TYPE_OPHYD)

        # additional params required for staff and user GUI panels to open without crashing the GUI
        setBeamlineConfigParam(beamline, 'robot_online', 0)
        setBeamlineConfigParam(beamline, config_params.TOP_VIEW_CHECK, 0)
        setBeamlineConfigParam(beamline, 'queueCollect', 0)
        setBeamlineConfigParam(beamline, 'vertRasterOn', 0)
        setBeamlineConfigParam(beamline, 'rasterProcessFlag', 0)
        setBeamlineConfigParam(beamline, 'fastDPNode1', 'cpu-001')
        setBeamlineConfigParam(beamline, 'fastDPNode2', 'cpu-002')
        setBeamlineConfigParam(beamline, 'fastDPNode3', 'cpu-003')
        setBeamlineConfigParam(beamline, 'fastDPNode4', 'cpu-004')
        setBeamlineConfigParam(beamline, 'spotNode1', 'cpu-004')
        setBeamlineConfigParam(beamline, 'spotNode2', 'cpu-004')
        setBeamlineConfigParam(beamline, 'spotNode3', 'cpu-004')
        setBeamlineConfigParam(beamline, 'spotNode4', 'cpu-004')
        setBeamlineConfigParam(beamline, 'spotNode5', 'cpu-004')
        setBeamlineConfigParam(beamline, 'spotNode6', 'cpu-004')
        setBeamlineConfigParam(beamline, 'spotNode7', 'cpu-004')
        setBeamlineConfigParam(beamline, 'spotNode8', 'cpu-004')

        setBeamlineConfigParam(beamline, config_params.CRYOSTREAM_ONLINE, 0)

def addGuiParams():
        setBeamlineConfigParam(beamline, 'screen_default_protocol', 'Screen')
        setBeamlineConfigParam(beamline, 'screen_default_phist', '0.0')
        setBeamlineConfigParam(beamline, 'screen_default_phi_end', '0.2')
        setBeamlineConfigParam(beamline, 'screen_default_width', '0.2')
        setBeamlineConfigParam(beamline, 'screen_default_dist', '137.0')
        setBeamlineConfigParam(beamline, 'screen_default_time', '0.02')
        setBeamlineConfigParam(beamline, 'screen_default_reso', '2.0')
        setBeamlineConfigParam(beamline, 'screen_default_wave', '1.0')
        setBeamlineConfigParam(beamline, 'screen_default_energy', '13.0')
        setBeamlineConfigParam(beamline, 'screen_default_beamWidth', '30')
        setBeamlineConfigParam(beamline, 'screen_default_beamHeight', '30')
        setBeamlineConfigParam(beamline, 'stdTrans', '0.1')
        setBeamlineConfigParam(beamline, 'beamstop_x_pvname', 'beamStopX')
        setBeamlineConfigParam(beamline, 'beamstop_y_pvname', 'beamStopY')

        #used only from GUI below?
        setBeamlineConfigParam(beamline, 'scannerType', 'Normal')
        setBeamlineConfigParam(beamline, 'attenType', 'RI')
        setBeamlineConfigParam(beamline, 'omegaMonitorPV', 'VAL')
        setBeamlineConfigParam(beamline, 'mountEnabled', '1')

if __name__ == '__main__':
    db_connect()

    #createTestDB()

    addBeamlineInfo()
    addCommParams()
    addCameraParams()
    addHardwareParams()
    addGuiParams()

