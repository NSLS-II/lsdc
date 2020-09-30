import ispyb.factory
from ispyb.exception import ISPyBNoResultException
import os
from datetime import datetime
from ispyb.xmltools import mx_data_reduction_to_ispyb, xml_file_to_dict
import daq_utils
from epics import PV
import db_lib
import time
import mysql.connector
import logging
logger = logging.getLogger(__name__)

#12/19 - I'm leaving all commented lines alone on this. Karl Levik, DLS, is an immense help with this.

conf_file = os.environ["CONFIGDIR"] + "ispybConfig.cfg"
visit = 'mx99999-1'
# Get a list of request dicts
#request_dicts = lsdb2.getColRequestsByTimeInterval('2018-02-14T00:00:00','2018-02-15T00:00:00')

# Connect to ISPyB, get the relevant data area objects
conn = ispyb.open(conf_file)
core = ispyb.factory.create_data_area(ispyb.factory.DataAreaType.CORE, conn)
mxacquisition = ispyb.factory.create_data_area(ispyb.factory.DataAreaType.MXACQUISITION, conn)
mxprocessing = ispyb.factory.create_data_area(ispyb.factory.DataAreaType.MXPROCESSING, conn)
mxscreening = ispyb.factory.create_data_area(ispyb.factory.DataAreaType.MXSCREENING, conn)
cnx = mysql.connector.connect(user='ispyb_api', password=os.environ['ISPYB_PASSWORD'],host='ispyb-db-dev',database='ispyb')
cursor = cnx.cursor()
beamline = os.environ["BEAMLINE_ID"]
detSeqNumPVNAME = db_lib.getBeamlineConfigParam(beamline,"detSeqNumPVNAME") #careful - this pvname is stored in DB and in detControl.
detSeqNumPV = PV(detSeqNumPVNAME)

  # Find the id for a particular

def queryOneFromDB(q):
  cursor.execute(q)
  try:
    return list(cursor.fetchone())[0]
  except TypeError:
    return 0

def personIdFromLogin(loginName):
  q = ("select personId from Person where login = \""+ loginName + "\"")
  return (queryOneFromDB(q))

def personIdFromProposal(propNum):
  q = ("select personId from Proposal where proposalNumber = " + str(propNum))
  return (queryOneFromDB(q))  

def proposalIdFromProposal(propNum):
  q = ("select proposalId from Proposal where proposalNumber = " + str(propNum))
  return (queryOneFromDB(q))

def maxVisitNumfromProposal(propNum):
  propID = proposalIdFromProposal(propNum)
  q = ("select max(visit_number) from BLSession where proposalId = " + str(propID))
  return (queryOneFromDB(q))
  

def createPerson(firstName,lastName,loginName):
  params = core.get_person_params()  
  params['given_name'] = firstName
  params['family_name'] = lastName
  params['login'] = loginName
  pid = core.upsert_person(list(params.values()))
  cnx.commit()
  

def createProposal(propNum,PI_login="boaty"):
  pid = personIdFromLogin(PI_login)
  if (pid == 0):
    createPerson("Not","Sure",PI_login)
    pid = personIdFromLogin(PI_login)
  params = core.get_proposal_params()
  params['proposal_code'] = 'mx'
  params['proposal_number'] = int(propNum)
  params['proposal_type'] = 'mx'
  params['person_id'] = pid
  params['title'] = 'SynchWeb Dev Proposal'
  proposal_id = core.upsert_proposal(list(params.values()))
  cnx.commit()  #not sure why I needed to do this. Maybe mistake in stored proc?

def createVisitName(propNum): # this is for the GUI to know what a datapath would be in row_clicked
  logger.info("creating visit Name for propnum " + str(propNum))
  propID = proposalIdFromProposal(propNum)
  if (propID == 0): #proposal doesn't exist, just create and assign to boaty
    createProposal(propNum)
  maxVis = maxVisitNumfromProposal(propNum)
  if (maxVis == None): #1st visit
    newVisitNum = 1
  else:
    newVisitNum = 1 + maxVis
    logger.info('new visit number: %s' % newVisitNum)
  visitName = "mx"+str(propNum)+"-"+str(newVisitNum)
  return visitName, newVisitNum


def createVisit(propNum):
  visitName, newVisitNum = createVisitName(propNum)
  personID = personIdFromProposal(propNum)
  params = core.get_session_for_proposal_code_number_params()
  params['proposal_code'] = 'mx'
  params['proposal_number'] = propNum
  params['visit_number'] = newVisitNum
  params['beamline_name'] = daq_utils.beamline.upper()
  params['startdate'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
  params['enddate'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
  
  params['comments'] = 'For software testing'
  sid = core.upsert_session_for_proposal_code_number(list(params.values()))
  cnx.commit() 
  assert sid is not None
  assert sid > 0
        # Test upsert_person:
#        params = core.get_person_params()
#        params['given_name'] = 'Baldur'
#        params['family_name'] = 'Odinsson'
#        params['login'] = 'bo%s' % str(time.time()) # login must be unique
#        pid = core.upsert_person(list(params.values()))
#        assert pid is not None
#        assert pid > 0

#        params = core.get_person_params()
#        params['id'] = pid
#        params['email_address'] = 'baldur.odinsson@asgard.org'
#        pid2 = core.upsert_person(list(params.values()))
#        assert pid2 is not None
#        assert pid2 == pid

        # Test upsert_session_has_person:
  params = core.get_session_has_person_params()
  params['session_id'] = sid
  params['person_id'] = personID
  params['role'] = 'Co-Investigator'
  params['remote'] = True
  core.upsert_session_has_person(list(params.values()))
  cnx.commit()
  try:
    personsOnProposalList = core.retrieve_persons_for_proposal("mx",propNum)
  except:
    return visitName      
  for i in range (0,len(personsOnProposalList)):
    personLogin = personsOnProposalList[i]["login"]
    personID = personIdFromLogin(personLogin)
    params = core.get_session_has_person_params()
    params['session_id'] = sid
    params['person_id'] = personID
    params['role'] = 'Co-Investigator'
    params['remote'] = True
    core.upsert_session_has_person(list(params.values()))
    cnx.commit()
    

        # Test upsert_proposal_has_person:
#        params = core.get_proposal_has_person_params()
#        params['proposal_id'] = 141666
#        params['person_id'] = pid
#        params['role'] = 'Principal Investigator'
#        phpid = core.upsert_proposal_has_person(list(params.values()))
#        assert phpid is not None
#        assert phpid > 0
  return visitName  

def addPersonToProposal(personLogin,propNum):
  personID = personIdFromLogin(personLogin)
  if (personID == 0):
    createPerson("Not","Sure",personLogin)
    personID  = personIdFromLogin(personLogin)
  propID = proposalIdFromProposal(propNum)
  if (propID == 0):
    createProposal(propNum,personLogin)
    propID = proposalIdFromProposal(propNum)    
  params = core.get_proposal_has_person_params()
  params['proposal_id'] = propID
  params['role'] = 'Co-Investigator'
  params['personid'] = personID
  phpid = core.upsert_proposal_has_person(list(params.values()))
  cnx.commit()                                          
  

def insertPlotResult(dc_id,imageNumber,spotTotal,goodBraggCandidates,method2Res,totalIntegratedSignal):
  params = mxprocessing.get_quality_indicators_params()
  params['datacollectionid'] = dc_id
  params['imageNumber'] = imageNumber
  params['spotTotal'] = spotTotal
  params['goodBraggCandidates'] = goodBraggCandidates
  params['method2Res'] = method2Res
  params['totalIntegratedSignal'] = totalIntegratedSignal
  id = mxprocessing.upsert_quality_indicators(list(params.values()))
  cnx.commit()         

def insertResult(result,resultType,request,visitName,dc_id=None,xmlFileName=None): #xmlfilename for fastDP
#keep in mind that request type can be standard and result type be fastDP - multiple results per req.

 cbfComm = db_lib.getBeamlineConfigParam(daq_utils.beamline,"cbfComm")
 try:
   sessionid = core.retrieve_visit_id(visitName)
 except ISPyBNoResultException as e:
   logger.error("caught ISPyBNoResultException: %s. make sure visit name is in the format mx999999-1234" % e)
   propNum = visitName.split('-')[0]
   sessionid = createVisit(propNum)
 request_type = request['request_type']
 if request_type in('standard', 'vector') :
   sample = request['sample'] # this needs to be created and linked to a DC group
   if (resultType == 'fastDP'):
     mx_data_reduction_dict = xml_file_to_dict(xmlFileName)
     (app_id, ap_id, scaling_id, integration_id) = mx_data_reduction_to_ispyb(mx_data_reduction_dict, dc_id, mxprocessing)
     params = mxprocessing.get_program_params()
     params['id'] = app_id
     params['status'] = 1
     mxprocessing.upsert_program(list(params.values()))
         
   elif resultType == 'mxExpParams':
     result_obj = result['result_obj']
     request_obj = result_obj['requestObj']
     directory = request_obj["directory"]
     filePrefix = request_obj['file_prefix']
     basePath = request_obj["basePath"]
     visitName = daq_utils.getVisitName()
     jpegDirectory = visitName + "/jpegs/" + directory[directory.find(visitName)+len(visitName):len(directory)]  
     fullJpegDirectory = basePath + "/" + jpegDirectory
     jpegImagePrefix = fullJpegDirectory+"/"+filePrefix     
     daq_utils.take_crystal_picture(filename=jpegImagePrefix)
     jpegImageFilename = jpegImagePrefix+".jpg"
     jpegImageThumbFilename = jpegImagePrefix+"t.jpg"
     node = db_lib.getBeamlineConfigParam(daq_utils.beamline,"adxvNode")
     comm_s = "ssh -q " + node + " \"convert " + jpegImageFilename + " -resize 40% " + jpegImageThumbFilename + "\"&"     
     logger.info('resizing image: %s' % comm_s)
     os.system(comm_s)
     seqNum = int(detSeqNumPV.get())          
     hdfSampleDataPattern = directory+"/"+filePrefix+"_" 
     hdfRowFilepattern = hdfSampleDataPattern + str(int(float(seqNum))) + "_master.h5"
     
# keep in mind I could do the jpeg conversion here, but maybe best to allow synchWeb on demand.
     cbfDir = directory
     CBF_conversion_pattern = cbfDir + "/" + filePrefix+"_"
     JPEG_conversion_pattern = fullJpegDirectory + "/" + filePrefix+"_"
     node = db_lib.getBeamlineConfigParam(daq_utils.beamline,"adxvNode")
     adxvComm = os.environ["PROJDIR"] + db_lib.getBeamlineConfigParam(daq_utils.beamline,"adxvComm")
     comm_s = "ssh -q " + node + " \"sleep 6;" + cbfComm + " "  + hdfRowFilepattern  + " 1:1 " + CBF_conversion_pattern + ";" + adxvComm + " -sa "  + CBF_conversion_pattern + "000001.cbf " + JPEG_conversion_pattern + "0001.jpeg;convert " + JPEG_conversion_pattern + "0001.jpeg -resize 10% " + JPEG_conversion_pattern + "0001.thumb.jpeg\"&"     
     logger.info('diffraction thumbnail image: %s' % comm_s)
     os.system(comm_s)
     # Create a new data collection group entry:
     params = mxacquisition.get_data_collection_group_params()
     params['parentid'] = sessionid
     if request_type == 'standard':
       params['experimenttype'] = 'OSC'
     elif request_type == 'vector':
       params['experimenttype'] = 'Helical'
     return createDataCollection(directory, filePrefix, jpegImageFilename, params, request_obj, sessionid)

                 ## For strategies (EDNA or otherwise)
                 # params = mxscreening.get_screening_params()
                 # params['dcgid'] = dcg_id
                 # ...
                 # s_id = mxscreening.insert_screening(list(params.values()))
                 # params = mxscreening.get_screening_input_params()
                 # params['screening_id'] = s_id
                 # ...
                 # s_in_id = mxscreening.insert_screening_input(list(params.values()))
                 # params = mxscreening.get_screening_output_params()
                 # params['screening_id'] = s_id
                 # ...
                 # s_out_id = mxscreening.insert_screening_output(list(params.values()))
                 # params = mxscreening.get_screening_output_lattice_params()
                 # params['screening_output_id'] = s_out_id
                 # ...
                 # mxscreening.insert_screening_output_lattice(list(params.values()))

                 # params = mxscreening.get_screening_strategy_params()
                 # params['screening_output_id'] = s_out_id
                 # ...
                 # s_s_id = mxscreening.insert_screening_strategy(list(params.values()))
                 # params = mxscreening.get_screening_strategy_wedge_params()
                 # params['screening_strategy_id'] = s_s_id
                 # ...
                 # s_s_wedge_id = mxscreening.insert_screening_strategy_wedge(list(params.values()))
                 # params = mxscreening.get_screening_strategy_sub_wedge_params()
                 # params['screening_strategy_wedge_id'] = s_s_wedge_id
                 # ...
                 # mxscreening.insert_screening_strategy_sub_wedge(list(params.values()))

                 ## For raster scans a.k.a. grid scans:
                 # params = mxacquisition.get_dc_position_params()
                 # params['id'] = dc_id
                 # params['posx'] =
                 # params['posy'] =
                 # params['posz'] =
                 # mxacquisition.update_dc_position(list(params.values()))

                 ## For per-image analysis results (raster scans or otherwise)
                 # for image in images:
                 #     params = mxprocessing.get_quality_indicators_params()
                 #     imq.imagenumber as nim, imq.method2res as res, imq.spottotal as s, imq.totalintegratedsignal, imq.goodbraggcandidates as b
                 #     params['imagenumber'] =
                 #     params['datacollectionid'] =
                 #     params['method2res'] =
                 #     params['spottotal'] =
                 #     params['totalintegratedsignal'] =
                 #     params['goodbraggcandidates'] =
                 #     mxprocessing.upsert_quality_indicators(list(params.values()))

                 ## For fast_dp and similar MX data reduction pipeline results:
                 # ...
                 # (app_id, ap_id, scaling_id, integration_id) = mx_data_reduction_to_ispyb(mx_data_reduction_dict, dc_id, mxprocessing)


                 ## For raster scans a.k.a. grid scans:
                 # params = mxacquisition.get_dcg_grid_params()
                 # params['parentid'] = dcg_id
                 # params['dx_mm'] =
                 # params['dy_mm'] =
                 # params['steps_x'] =
                 # params['steps_y'] =
                 # params['pixelspermicronx'] =
                 # params['pixelspermicrony'] =
                 # params['snapshot_offsetxpixel'] =
                 # params['snapshot_offsetypixel'] =
                 # params['orientation'] =
                 # params['snaked'] =
                 # mxacquisition.upsert_dcg_grid(list(params.values()))


                 # Beamsize:
                 # params['beamsize_at_samplex'] = ?
                 # params['beamsize_at_sampley'] = ?

                 # Other things:
                 # params['xbeam'] = ?
                 # params['ybeam'] = ?
                 # params['phistart'] = ?
                 # params['kapppastart'] = ?
                 # params['omegastart'] = ?

       # hard-coding hack to make SynchWeb understand whether it's a full data collection or a screening


def createDataCollection(directory, filePrefix, jpegImageFilename, params, request_obj, sessionid):
    params['starttime'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    params['endtime'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    dcg_id = mxacquisition.insert_data_collection_group(list(params.values()))
    logger.info("dcg_id: %i" % dcg_id)
    params = mxacquisition.get_data_collection_params()
    params['parentid'] = dcg_id
    params['visitid'] = sessionid
    params['imgdir'] = directory
    params['imgprefix'] = filePrefix
    params['imgsuffix'] = 'cbf'  # assume CBF ...?
    params['wavelength'] = request_obj['wavelength']
    params['starttime'] = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    params['run_status'] = 'DataCollection Successful'  # assume success / not aborted
    params['datacollection_number'] = request_obj['runNum']
    params['n_images'] = int(round((request_obj['sweep_end'] - request_obj['sweep_start']) / request_obj['img_width']))
    params['exp_time'] = request_obj['exposure_time']
    params['start_image_number'] = request_obj['file_number_start']
    params['axis_start'] = request_obj['sweep_start']
    params['axis_end'] = request_obj['sweep_end']
    params['axis_range'] = request_obj['img_width']
    params['resolution'] = request_obj['resolution']
    params['detector_distance'] = request_obj['detDist']
    params['slitgap_horizontal'] = request_obj['slit_width']
    params['slitgap_vertical'] = request_obj['slit_height']
    params['transmission'] = request_obj['attenuation'] * 100.0
    params['file_template'] = '%s_####.cbf' % (request_obj['file_prefix'])  # assume cbf ...
    params['overlap'] = 0.0
    params['rotation_axis'] = 'Omega'  # assume Omega unless we know otherwise
    logger.info("jpegimfilename = " + jpegImageFilename)
    params['xbeam'] = request_obj['xbeam']
    params['ybeam'] = request_obj['ybeam']
    params['xtal_snapshot1'] = jpegImageFilename
    params['xtal_snapshot2'] = '/dls/i03/data/2016/cm14451-2/jpegs/20160413/test_xtal/xtal1_1_1_90.0.png'
    params['xtal_snapshot3'] = '/dls/i03/data/2016/cm14451-2/jpegs/20160413/test_xtal/xtal1_3_1_183.0.png'
    params['xtal_snapshot4'] = '/dls/i03/data/2016/cm14451-2/jpegs/20160413/test_xtal/xtal1_3_1_93.0.png'
    dc_id = mxacquisition.insert_data_collection(list(params.values()))
    logger.info("dc_id: %i" % dc_id)
    return dc_id


#         if request_type == 'screening':
#           params['overlap'] = 89.0
                 
def insertRasterResult(result,request,visitName): 

 try:
   sessionid = core.retrieve_visit_id(visitName)
 except ISPyBNoResultException as e:
   logger.error("caught ISPyBNoResultException, make sure visit name is in the format mx999999-1234. bye: %s" % e)
   return
 sample = request['sample'] # this needs to be created and linked to a DC group
 result_obj = result['result_obj']
 request_obj = request['request_obj']
 directory = request_obj["directory"]
 filePrefix = request_obj['file_prefix']
 basePath = request_obj["basePath"]
 visitName = daq_utils.getVisitName()
 jpegDirectory = visitName + "/jpegs/" + directory[directory.find(visitName)+len(visitName):len(directory)]  
 fullJpegDirectory = basePath + "/" + jpegDirectory
 jpegImagePrefix = fullJpegDirectory+"/"+filePrefix     
 jpegImageFilename = jpegImagePrefix+".jpg"
 jpegImageThumbFilename = jpegImagePrefix+"t.jpg"
 comm_s = "convert " + jpegImageFilename + " -resize 40% " + jpegImageThumbFilename + "&"     
 logger.info('raster thumbnail creation: %s' %comm_s)
 os.system(comm_s)
 # Create a new data collection group entry:
 params = mxacquisition.get_data_collection_group_params()
 params['parentid'] = sessionid
 params['experimenttype'] = 'OSC'
 return createDataCollection(directory, filePrefix, jpegImageFilename, params, request_obj, sessionid)
