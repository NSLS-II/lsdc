
import time
import os

import sys

import traceback

from mongoengine import NotUniqueError

from db_lib import *  # makes db connection


def createTestDB():
        db_connect()
        createBeamline("fmx", "17id1")
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



        beamlineInfo('fmx', 'mountedSample', info_dict={'puckPos': 0, 'pinPos': 0,
                                                         'sampleID': -99})



if __name__ == '__main__':
    createTestDB()

