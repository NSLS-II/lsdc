
from datetime import (datetime, timedelta)
import time
import db_lib
from collections import Counter
import dateutil.parser
import logging
logger = logging.getLogger(__name__)

#12/19 skinner didn't write this. Maybe Annie. Ask Matt.

def validate_date(d):
    """
    This will convert about any date to be isoformat
    this will take '2017-jul-12', '12-jul-2017', 'Jul-12-2017' and convert to '2017-07-12T00:00:00'
                   '2017-07-12' or '2017-07-12T00' and convert to '2017-07-12T00:00:00'
    **it will not know which is the day,mont in the 07-12-2017**
    """
    try:
        datetime.strptime(d, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        new_d = dateutil.parser.parse(d)
        d = new_d.isoformat()
        logger.info('new formated date {}'.format(d))
    return d


def getResultsByTimeInterval(start_thuman, end_thuman = None):
    """
      In order to limit our querys, get headers results for an interval of time.
    :params  start_thuman, required
    :params  end_thuman opt. default to now
     format is friendlier than timestamp 'yyyy-mm-ddThh:mm' (hours 0-24)
    :return list of full headers:  format list of dict
    """
    # validate and convert to isoformat
    start_thuman = validate_date(start_thuman)

    start_t = time.mktime(datetime.strptime(start_thuman, '%Y-%m-%dT%H:%M:%S').timetuple())

    if end_thuman is None:
        now = datetime.now()
        end_t =time.mktime(now.timetuple())

    else:
        end_thuman = validate_date(end_thuman)
        end_t = time.mktime(datetime.strptime(end_thuman, '%Y-%m-%dT%H:%M:%S').timetuple())
        logger.info(end_t)
        logger.info(start_t)
    headers = list(db_lib.analysis_ref.find_analysis_header(time={'$lt': end_t, '$gte': start_t}))
    return headers


def getColRequestsByTimeInterval(start_thuman, end_thuman = None):
    """
     In order to limit our querys, get headers for requests for an interval of time.
    :params  start_thuman, required
    :params  end_thuman opt. default to now
     format is friendlier than timestamp 'yyyy-mm-ddThh:mm' (hours 0-24)
    :return list of full headers:  format list of dict
    """
    # validate and convert to isoformat
    start_thuman = validate_date(start_thuman)

    start_t = time.mktime(datetime.strptime(start_thuman, '%Y-%m-%dT%H:%M:%S').timetuple())

    if end_thuman is None:
        now = datetime.now()
        end_t =time.mktime(now.timetuple())

    else:
        end_thuman = validate_date(end_thuman)
        end_t = time.mktime(datetime.strptime(end_thuman, '%Y-%m-%dT%H:%M:%S').timetuple())
    headers = list(db_lib.request_ref.find(time={'$lt': end_t, '$gte': start_t},request_type={'$in':['standard','vector']},priority=-1))
    return headers

def getAllRequestsByTimeInterval(start_thuman, end_thuman = None):
    """
     In order to limit our querys, get headers for requests for an interval of time.
    :params  start_thuman, required
    :params  end_thuman opt. default to now
     format is friendlier than timestamp 'yyyy-mm-ddThh:mm' (hours 0-24)
    :return list of full headers:  format list of dict
    """
    # validate and convert to isoformat
    start_thuman = validate_date(start_thuman)

    start_t = time.mktime(datetime.strptime(start_thuman, '%Y-%m-%dT%H:%M:%S').timetuple())

    if end_thuman is None:
        now = datetime.now()
        end_t =time.mktime(now.timetuple())

    else:
        end_thuman = validate_date(end_thuman)
        end_t = time.mktime(datetime.strptime(end_thuman, '%Y-%m-%dT%H:%M:%S').timetuple())
    headers = list(db_lib.request_ref.find(time={'$lt': end_t, '$gte': start_t},priority=-1))
    return headers


def getMountCount(start_thuman, end_thuman, beamline):

    reqs = getResultsByTimeInterval(start_thuman, end_thuman)
    mountCount=0
    currentSampID = ""
    for i in range (0,len(reqs)):
      try:
        if (reqs[i]["beamline"] == beamline):
          sampID = reqs[i]["sample"]
          if (sampID != currentSampID):
            mountCount+=1
            currentSampID = sampID
      except KeyError:
        logger.info(reqs[i])
    return mountCount

      
      
    


def printColRequestsByTimeInterval(start_thuman, end_thuman = None, fname = "sweeps.txt"):
    reqs = getColRequestsByTimeInterval(start_thuman, end_thuman)
    outfile = open(fname,"w+")
    outfile.write("proposalID\tdirectory\tprefix\tprotocol\tnumFrames\texptime\timgWidth\tomegaStart\ttranslation\txvec\tyvec\tzvec\tsysTime\ttimestamp\n")    
    for i in range (0,len(reqs)):
      propID = reqs[i]["proposalID"]
      reqObj = reqs[i]['request_obj']
      exptime = reqObj['exposure_time']
      imgWidth = reqObj['img_width']
      sweep_start = reqObj['sweep_start']
      sweep_end = reqObj['sweep_end']
      prefix = reqObj['file_prefix']
      directory = reqObj['directory']
      protocol = reqObj['protocol']
      if (protocol == "vector"):
        translation = reqObj['vectorParams']['trans_total']
        xvec = reqObj['vectorParams']['x_vec']
        yvec = reqObj['vectorParams']['y_vec']
        zvec = reqObj['vectorParams']['z_vec']        
      else:
        translation = 0.0
        xvec = 0.0
        yvec = 0.0
        zvec = 0.0        
      numimages = (sweep_end-sweep_start)/imgWidth
      systemTime = reqs[i]["time"]
      time_s = time.ctime(systemTime)
      line = str(propID) + "\t" + directory + "\t" + prefix + "\t" + protocol + "\t" + str(numimages) + "\t" + str(exptime) + "\t" + str(imgWidth) + "\t" + str(sweep_start) + "\t" + str(translation) + "\t" + str(xvec) + "\t" + str(yvec) + "\t" + str(zvec) + "\t" + str(systemTime) + "\t" + time_s + "\n"
      outfile.write(line)
      logger.info(line)
    logger.info(str(len(reqs)) + " requests")
    outfile.close()
    

def getRasterRequestsByTimeInterval(start_thuman, end_thuman = None):
    """
     In order to limit our querys, get headers for requests for an interval of time.
    :params  start_thuman, required
    :params  end_thuman opt. default to now
     format is friendlier than timestamp 'yyyy-mm-ddThh:mm' (hours 0-24)
    :return list of full headers:  format list of dict
    """
    # validate and convert to isoformat
    start_thuman = validate_date(start_thuman)

    start_t = time.mktime(datetime.strptime(start_thuman, '%Y-%m-%dT%H:%M:%S').timetuple())

    if end_thuman is None:
        now = datetime.now()
        end_t =time.mktime(now.timetuple())

    else:
        end_thuman = validate_date(end_thuman)
        end_t = time.mktime(datetime.strptime(end_thuman, '%Y-%m-%dT%H:%M:%S').timetuple())
    headers = list(db_lib.request_ref.find(time={'$lt': end_t, '$gte': start_t},request_type='raster'))
    return headers


def getAllRequestsByTimeInterval(start_thuman, end_thuman = None):
    """
     In order to limit our querys, get headers for requests for an interval of time.
    :params  start_thuman, required
    :params  end_thuman opt. default to now
     format is friendlier than timestamp 'yyyy-mm-ddThh:mm' (hours 0-24)
    :return list of full headers:  format list of dict
    """
    # validate and convert to isoformat
    start_thuman = validate_date(start_thuman)

    start_t = time.mktime(datetime.strptime(start_thuman, '%Y-%m-%dT%H:%M:%S').timetuple())

    if end_thuman is None:
        now = datetime.now()
        end_t =time.mktime(now.timetuple())

    else:
        end_thuman = validate_date(end_thuman)
        end_t = time.mktime(datetime.strptime(end_thuman, '%Y-%m-%dT%H:%M:%S').timetuple())
    headers = list(db_lib.request_ref.find(time={'$lt': end_t, '$gte': start_t},priority=-1))
    return headers


def getSampleReqRes(reqid):
    """
    this function is used in the getVisitSummary.
    the requestid is present in the request and in the results
    if you don't have a list of requestid , you can try :
    reqid = db_lib.getRequestsBySampleID(value, active_only=False
    :params reqid is a list of requestid per sample
    """

    logger.info('**New sample**')

    if reqid != []:
        logger.info('{:12} {:15} {:10}'.format('ProposalID', 'Sample Name', 'Sample ID'))
        for r in reqid:
            if r is not None:
                logger.info('{:_>50}'.format(''))
                sample_name = db_lib.getSampleNamebyID(r['sample'])
                logger.info('{:12} {:15} {:10}'.format(r['proposalID'], sample_name, r['uid']))
                reqRes = db_lib.getRequestByID(str(r['uid']), active_only = False)
                FASTDP = 'no'  # default
                try:
                    FASTDP == reqRes['request_obj']['fastDP']
                except KeyError as e:
                    logger.info(" no FASTDP key " + repr(e))
                logger.info('{:>20} {:6} {:12} {:12}{:6} {:>6}-{:6}'.format('requests', 'FastDP', 'wavelength A',
                                                                      'DetDist mm','width (Deg)', 'Start','End' ))
                logger.info('{:>20} {:<6} {:10} {:10}{:6} {:>10}-{:6}'.format(r['request_type'], FASTDP,
                                                                        reqRes['request_obj']['wavelength'],
                                                                        reqRes['request_obj']['detDist'],
                                                                        reqRes['request_obj']['img_width'],
                                                                        reqRes['request_obj']['sweep_start'],
                                                                        reqRes['request_obj']['sweep_end']))
                logger.info('{:*>20}'.format('Results'))
                try:
                    reqres = db_lib.getResultsforRequest(r['uid'])
                    for rr in reqres:
                        logger.info('{:>20}'.format(rr['result_type']))
                        # eventually it might be important to show what kind of results was obtained from the raster
                        if rr['result_type'] == 'rasterResult':
                            logger.info('{:>38}'.format(rr['result_obj']['rasterCellResults']['type']))
                except Exception as e:
                    logger.info('in 2nd exception')
                    logger.info('{:20}'.format('none'))


def getSamplesByTimeInterval(start_thuman, end_thuman = None):
    """
    get a unique list of sampleids associated with a proposal 'collected on" during an interval of time i.e
    no discremination about the result_type

    will parse the headers from et ResultsByTimeInterval
    return: a dict {'proposalid':[sampleid]}
    """
    headers = getResultsByTimeInterval(start_thuman, end_thuman)
    dict_ps = {}
    for p in headers:
        if p['proposalID']:
            key = p['proposalID']
            if p['proposalID'] is not None:
                if p['sample'] is not None:
                    sample = p['sample']
                    dict_ps.setdefault(key, list(set([]))).append(sample)

    num_samples = ''
    for k, v in dict_ps.items():

        #  make unique list of sampleid per proposal
        dict_ps[k] = list(set(v))

        # get some stats
        num_samples = len(list(set(v)))
        logger.info('proposalid {} had {} samples'.format(k, num_samples))
    num_proposal = len(dict_ps.keys())
    proposals = dict_ps.keys()
    data = {"num_proposal": num_proposal, "proposals": proposals, "dict_samples": dict_ps}
    return dict_ps


def getVisitSummary(start_thuman, end_thuman = None):
    """
     Getting a summary of request and Results on samples collected during a visit WIP
    :param start_thuman: required start time for the visit , format 'yyyy-mm-ddThh:mm'
    :param end_thuman: opt if None defaults to now
    :return: for now a screen print out, format to be determined , file that we can send?
    """
    sampleid_dict = getSamplesByTimeInterval(start_thuman, end_thuman) #this probably eliminates test samples.

    for proposalid, sid in sampleid_dict.items(): 
        logger.info("proposal : %s" % proposalid)
        for value in sid:
            # getting a list of all the requests for a sample

            # todo need to limit for the period

            reqid = db_lib.getRequestsBySampleID(value, active_only=False)
            try:
                sampleInfo = getSampleReqRes(reqid)
            except Exception as e:
                logger.info('problem with sample info ' + repr(e))



def getShortVisitSummary(start_thuman, end_thuman=None):
    """
     Get more generic statistics, on the mx beamlines, get a printed summary of what was done
    :param start_thuman:
    :param end_thuman:
    :return: a list of dict for each proposalid worked on. This is for both beamlines (amx fmx)
    """

    # get the headers
    sampleid_dict = getSamplesByTimeInterval(start_thuman, end_thuman)

    visits = []  # will have the stats for a visit according to proposalid.

   #  headers for the print
    logger.info('{:25} {:10} {:10} {:^10}{:^10} {:^10} {:^10} {:10}'.format('Name', 'proposalid', 'standard', 'raster', 'snapshot', 'vector', 'escan', 'sample ID'))

    for pid, sid in sampleid_dict.items():
        num_samples = (len(sid))

     # define timestamps for now start-end
        p_stime = time.time()
        p_etime = 1451624400.0 #     '2016-01-01T00:00'

        num_datacol = 0

        for value in sid:
            # getting the name of the samples
            sample_name =  db_lib.getSampleNamebyID(value)

            # getting a flavor of the request type
            list_type =[]
            srt = db_lib.getRequestsBySampleID(value, active_only=False)  # at this point it's not discriminating with time
            num_datacol += len(srt)


            # find the request_type for each header
            for i in srt:
                try:
                    req_type = i['request_type']
                except Exception as e:
                    req_type = 'none'

                # set the time period for a proposal
                start_thuman = validate_date(start_thuman)
                start_t = time.mktime(datetime.strptime(start_thuman, '%Y-%m-%dT%H:%M:%S' ).timetuple())

                if end_thuman is None:
                    now = datetime.now()
                    end_t =time.mktime(now.timetuple())

                else:
                   end_thuman = validate_date(end_thuman)
                   end_t = time.mktime(datetime.strptime(end_thuman, '%Y-%m-%dT%H:%M:%S').timetuple())

                if  i['time'] >= start_t  and 	i['time'] <= end_t:

                    # set the time period for a proposal

                    if i['time'] <= p_stime:
                        p_stime = i['time']
                    if i['time'] >= p_etime:
                        p_etime = i['time']


                    list_type.append(req_type)
                p_stime2 = datetime.fromtimestamp(p_stime).strftime('%Y-%m-%dT%H:%M:%S')
                p_etime2 = datetime.fromtimestamp(p_etime).strftime('%Y-%m-%dT%H:%M:%S')

                visit = {'pid': pid, 'num_datacol': num_datacol, 'beamline': 'amx', 'num_samples': num_samples,'start': p_stime2, 'end': p_etime2}

            list_type = Counter(list_type)

            standard = ''
            raster = ''
            escan  = ''
            vector = ''
            snapshot = ''

            if 'standard' in list_type:
                    standard = list_type['standard']
            if 'raster' in list_type:
                    raster = list_type['raster']
            if 'vector' in list_type:
                    vector = list_type['vector']
            if 'snapshot' in list_type:
                    snapshot = list_type['snapshot']
            if 'escan' in list_type:
                    escan = list_type['escan']

            logger.info('{:25} {:^10} {:^10} {:^10} {:^10} {:^10} {:^10}{:10}'.format(sample_name, pid,  standard, raster, snapshot, vector, escan, value))
        visits.append(visit)
        logger.info('----------{} samples, {} requests from {} to {} '.format(num_samples, num_datacol, p_stime2, p_etime2 ))

    return visits



def getRequestsbyProposalID(proposalID, active_only=False):
    """
    :param proposalID required int, 6 digits
    :return a list of dict (headers)
    """
    params = {'proposalID': proposalID}
    if active_only:
        params['state'] = "active"
    reqs = list(db_lib.request_ref.find(**params))
    return reqs


def getSamplesbyProposalID(proposalID):
    """
    since proposalids are not included with the samples, they need to have a request attached to them
    so, query for request with that proposalid and then extract the sampleid
    do we need to attach the owner to the sample?

    :params proposalID in theorie from PASS str(6 digits)
    :return  list of sampleid

    """
    reqs = getRequestsbyProposalID(proposalID, active_only=False)
    if reqs !=[]:
        list_sampleid = []
        for i in reqs:
            list_sampleid.append(i['sample'])
        logger.info('proposal {} has {} samples '.format(proposalID, len(list_sampleid)))
    data = { 'proposalID': proposalID, 'num_samples': len(list_sampleid), 'list_sampleid': list_sampleid}
    return list_sampleid


# def getBeamlineforProposalID(proposalID):
#     """
#     """
#     reqs = getRequestsbyProposalID(proposalID, active_only=False)
#     if reqs !=[]:
#         list_beamline = []
#         for i in reqs:
#             list_beamline.append(i['beamline'])
