
import time
import os

import sys

import traceback

from mongoengine import NotUniqueError

from db_lib import *  # makes db connection


def createTestDB():
        db_connect()
        beamline = "fmx"
        createBeamline(beamline, "17id1")
#        createBeamline("amx", "17id2")        
#        createBeamline("john", "99id1")
        owner = 'john'
        
        
        # containers
        for i in range(1,5):  # 1 indexed, discontinuity for testing
            containerName = 'Puck_{0}'.format(i)
            createContainer(containerName, 16, owner, kind='16_pin_puck')

        for i in range(1,5):  # discontinuity for testing
            containerName = 'dewar_{0}'.format(i)
            createContainer(containerName, 100, owner, kind='shipping_dewar') # I don't know dewar capacity


        # named containers
        primary_dewar_name = 'primaryDewar'

        createContainer("primaryDewar", 24, owner, kind='24_puck_robot_dewar')
        createContainer("primaryDewarAMX", 24, owner, kind='24_puck_robot_dewar')
        createContainer("primaryDewarFMX", 24, owner, kind='24_puck_robot_dewar')
        

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
                    sampID = createSample(sampleName, owner, kind='24_puck_robot_dewar', sample_type=type_name)

                except NotUniqueError:
                    raise NotUniqueError('{0}'.format(sampleName))

                if not insertIntoContainer(containerName, owner, j, sampID):
                    print('name {0}, pos {1}, sampid {2}'.format(containerName, j, sampID))



        #setBeamlineConfigParam(beamline, 'mountedSample', {'puckPos': 0, 'pinPos': 0, 'sampleID': -99}) #mountedSample has no val... why??
        beamlineInfo(beamline, 'mountedSample', {'puckPos': 0, 'pinPos': 0, 'sampleID': '-99'})
        beamlineInfo(beamline, 'rasterScoreFlag',{'index':0} )
        setBeamlineConfigParam(beamline, 'dewarPlateMap', {'0':[180,-180], '1':[135,225], '2':[90,-270], '3':[45,-315], '4':[0,360], '5':[315,-45], '6':[270,90], '7':[225,-135]})
        setBeamlineConfigParam(beamline, 'dewarPlateName', 'dewarPlateJohn')
        setBeamlineConfigParam(beamline, 'lowMagCamURL', 'http://xf17id1c-ioc2.cs.nsls2.local:8007/C2.MJPG.mjpg')
        setBeamlineConfigParam(beamline, 'highMagCamURL', 'http://xf17id1c-ioc2.cs.nsls2.local:8008/C2.MJPG.mjpg')
        setBeamlineConfigParam(beamline, 'highMagZoomCamURL', 'http://xf17id1c-ioc2.cs.nsls2.local:8008/C1.MJPG.mjpg')
        setBeamlineConfigParam(beamline, 'lowMagZoomCamURL', 'http://xf17id1c-ioc2.cs.nsls2.local:8007/C3.MJPG.mjpg')
        setBeamlineConfigParam(beamline, 'lowMagFOVx', '1450')
        setBeamlineConfigParam(beamline, 'lowMagFOVy', '1160')
        setBeamlineConfigParam(beamline, 'highMagFOVx', '380')
        setBeamlineConfigParam(beamline, 'highMagFOVy', '300')
        setBeamlineConfigParam(beamline, 'lowMagPixX', '640')
        setBeamlineConfigParam(beamline, 'lowMagPixY', '512')
        setBeamlineConfigParam(beamline, 'highMagPixX', '640')
        setBeamlineConfigParam(beamline, 'highMagPixY', '512')
        setBeamlineConfigParam(beamline, 'screenPixX', '640')
        setBeamlineConfigParam(beamline, 'screenPixY', '512')
        setBeamlineConfigParam(beamline, 'beamlineComm', 'XF:17IDC-ES:FMX{Comm}')
        setBeamlineConfigParam(beamline, 'gonioPvPrefix', 'XF:17IDC-ES:FMX')
        setBeamlineConfigParam(beamline, 'detector_id', 'EIGER-16')
        setBeamlineConfigParam(beamline, 'detRadius', '116.0')
        setBeamlineConfigParam(beamline, 'detector_type', 'pixel_array')
        setBeamlineConfigParam(beamline, 'imgsrv_port', '14007')
        setBeamlineConfigParam(beamline, 'imgsrv_host', 'x25-h.nsls.bnl.gov')
        setBeamlineConfigParam(beamline, 'has_edna', '1')
        setBeamlineConfigParam(beamline, 'has_beamline', '0')
        setBeamlineConfigParam(beamline, 'detector_offline', '0')
        setBeamlineConfigParam(beamline, 'has_xtalview', '1')
        setBeamlineConfigParam(beamline, 'camera_offset', '0.0')
        setBeamlineConfigParam(beamline, 'xtal_url_small', 'http://xf17id1c-ioc2.cs.nsls2.local:8008/C2.MJPG.jpg')
        setBeamlineConfigParam(beamline, 'xtal_url', 'http://xf17id1c-ioc2.cs.nsls2.local:8007/C2.MJPG.jpg')
        setBeamlineConfigParam(beamline, 'mono_mot_code', 'mon')
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

        


if __name__ == '__main__':
    createTestDB()

