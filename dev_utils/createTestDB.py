#!/usr/bin/env python
####!/usr/bin/python
from __future__ import (absolute_import, print_function)

import time
import os

import sys
#sys.path.append('/h/cowan/projects')  # until we get this packaged+installed

import traceback

#from odm_templates import collections

#import lsdc.db_lib  # makes db connection
from db_lib import *  # makes db connection


def createTestDB():
        db_connect()
#        createBeamline("fmx", "17id1")
#        createBeamline("amx", "17id2")        
#        createBeamline("john", "99id1")
        
        
        # containers
        for i in range(1,5):  # 1 indexed, discontinuity for testing
            containerName = 'Puck_{0}'.format(i)
            createContainer(containerName, 16, kind='16_pin_puck')

        for i in range(1,5):  # discontinuity for testing
            containerName = 'dewar_{0}'.format(i)
            createContainer(containerName, 100,kind='shipping_dewar') # I don't know dewar capacity


        # named containers
        primary_dewar_name = 'primaryDewar'

        createContainer("primaryDewar", 24,kind='24_puck_robot_dewar')
        createContainer("primaryDewarAMX", 24,kind='24_puck_robot_dewar')
        createContainer("primaryDewarFMX", 24,kind='24_puck_robot_dewar')
        

        for i in range(1,5):  # discontinuity for testing
            containerName = 'Puck_{0}'.format(i)
            insertIntoContainer(primary_dewar_name, i, getContainerIDbyName(containerName))


        # samples
        type_name = 'pin'
        for i in range(1,4):  # discontinuity for testing
            containerName = 'Puck_{0}'.format(i)
            for j in range(1,5):
                sampleName = 'samp_{0}_{1}'.format(i, j)

                try:
                    sampID = createSample(sampleName, sample_type=type_name)

                except NotUniqueError:
                    raise NotUniqueError('{0}'.format(sampleName))

                if not insertIntoContainer(containerName, j, sampID):
                    print('name {0}, pos {1}, sampid {2}'.format(containerName, j, sampID))



        beamlineInfo('john', 'mountedSample', info_dict={'puckPos': 0, 'pinPos': 0,
                                                         'sampleID': -99})



if __name__ == '__main__':
    createTestDB()

