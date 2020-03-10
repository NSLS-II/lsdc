#!/usr/bin/env python
####!/usr/bin/python
from __future__ import (absolute_import, print_function)

import traceback

#from odm_templates import collections

#import lsdc.db_lib  # makes db connection
from db_lib import *  # makes db connection


def createTestDB():
    try:
        # fields
        base_fields = [{'name': 'name', 'description': 'a short, human readable name',
                        'bson_type': 'String'},
                      {'name': 'description', 'description': 'a shortish explanatory text',
                        'bson_type': 'String'},
                      {'name': 'priority',
                       'description': 'positive integer, higher number=higher priority',
                       'bson_type': '64-bit integer?'},
                      {'name': 'capacity',
                       'description': 'postitive integer, number of sample positions within the container',
                       'bson_type': '64-bit integer?'}]

        for f in  base_fields:
            print('name: {0}'.format(f['name']))
            createField(f['name'], f['description'], f['bson_type'])


        # base types
        parent_types = [{'name': 'sample', 'description': '', 'parent_type': 'base'},
                      {'name': 'container', 'description': '', 'parent_type': 'base'},
                      {'name': 'request', 'description': '', 'parent_type': 'base'},
                      {'name': 'result', 'description': '', 'parent_type': 'base'}]  # 'location'?

        for t in  parent_types:
            print('name: {0}'.format(t['name']))
            createType(t['name'], t['description'], t['parent_type'])


        types = [{'name': 'puck',
                  'description': 'generic hockey puck style subcontainer for shipping dewars',
                  'parent_type': 'container'},
                 {'name': 'pin', 'description': '', 'parent_type': 'sample'},
                 {'name': 'standard_pin', 'description': '', 'parent_type': 'pin'},
                 {'name': 'dewar', 'description': '', 'parent_type': 'container'},
                 {'name': 'shipping_dewar', 'description': '', 'parent_type': 'dewar'},
                 {'name': 'test_request', 'description': '', 'parent_type': 'request'},
                 {'name': 'test_result', 'description': '', 'parent_type': 'result'}]

        for t in types:
            print('name: {0}, parent_type {1}'.format(t['name'], t['parent_type']))
            createType(t['name'], t['description'], t['parent_type'])


        # containers with a fixed number of sample or subcontainer locations
        types = [{'name': '16_pin_puck',
                  'description': 'original 16 pin puck',
                  'parent_type': 'puck', 'capacity': 16},
                 {'name': '24_puck_robot_dewar',
                  'description': '24 puck dewar',
                  'parent_type': 'dewar', 'capacity': 24},
                 {'name': '5_slot_cane',
                  'description': 'traditional, 5 position cane for pins in vials',
                  'parent_type': 'container', 'capacity': 5}]

        for t in types:
            print('name: {0}, parent_type {1}'.format(t['name'], t['parent_type']))
            createType(t['name'], t['description'], t['parent_type'], capacity=t['capacity'])
        createType("raster","","request")        
        createType("standard","","request")        
        createType("vector","","request")        
        createType("characterize","","request")        
        createType("ednaCol","","request")
        createType("multiCol","","request")
        createType("eScan","","request")                        
        createType("screen","","request")        
        createType("snapshot","","request")        
        createType("snapshotResult","","result")        
        createType("xia2","","result")        
        createType("fastDP","","result")
        createType("choochResult","","result")                
        createType("dials","","result")        
        createType("diffImageJpeg","","result")        
        createType("xtalpicJpeg","","result")        
        createType("rasterJpeg","","result")        
        createType("rasterResult","","result")             
        createType("characterizationStrategy","","result")        
        createType("mxExpParams","","result")
        createType("eScanResult","","result")        
        

        createBeamline("fmx", "17id1")
        createBeamline("amx", "17id2")        
        createBeamline("john", "99id1")
        
        
        # containers
        for i in range(1,5)+[7]:  # 1 indexed, discontinuity for testing
            containerName = 'Puck_{0}'.format(i)
            createContainer(containerName, '16_pin_puck')

        for i in range(1,5):  # discontinuity for testing
            containerName = 'dewar_{0}'.format(i)
            createContainer(containerName, 'shipping_dewar')


        # named containers
#        primary_dewar_name = 'primaryDewar'

        createContainer("primaryDewar", '24_puck_robot_dewar')
        createContainer("primaryDewarAMX", '24_puck_robot_dewar')
        createContainer("primaryDewarFMX", '24_puck_robot_dewar')
        

        for i in range(1,5)+[7]:  # discontinuity for testing
            containerName = 'Puck_{0}'.format(i)
            insertIntoContainer(primary_dewar_name, i, getContainerIDbyName(containerName))


        # samples
        type_name = 'pin'
        for i in range(1,4)+[7]:  # discontinuity for testing
            containerName = 'Puck_{0}'.format(i)
            for j in range(1,5)+[7]:
                sampleName = 'samp_{0}_{1}'.format(i, j)

                try:
                    sampID = createSample(sampleName, sample_type=type_name)

                except NotUniqueError:
                    raise NotUniqueError('{0}'.format(sampleName))

                if not insertIntoContainer(containerName, j, sampID):
                    print('name {0}, pos {1}, sampid {2}'.format(containerName, j, sampID))


        # bare requests
#        request_type = 'test_request'
#        request_id = createRequest(request_type,
#                                   {'test_request_param': 'bare request 1'},
#                                   as_mongo_obj=True)
        
        # bare results
#        result_type = 'test_result'
#        createResult(result_type, request_id,
#                      {'test_result_value': 'bare result 1'})

        # in requestList on sample

#        request_id = addRequesttoSample(sampID,
#                                 request_type,
#                                 {'test_request_param': 'test param 1'},
#                                 as_mongo_obj=True)

        # in requestList on sample
#        request_id = addRequesttoSample(sampID,
#                                 request_type,
#                                 {'test_request_param': 'test param 2'},
#                                 as_mongo_obj=True)
        
        # in resultsList on sample
#        addResultforRequest(result_type, request_id,
#                             {'test_result_val': 'test val 1'})

        beamlineInfo('john', 'mountedSample', info_dict={'puckPos': 0, 'pinPos': 0,
                                                         'sampleID': -99})


    except Exception as e:
        print('Warning! caught exception, dropping incomplete db!\n\n{0}\n'.format(e))
        traceback.print_exc()
        print('\n')

        # drop incomplete database
        mongo_conn.drop_database(db_name)


if __name__ == '__main__':
    createTestDB()

