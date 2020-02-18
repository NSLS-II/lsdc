#!/opt/conda_envs/lsdc_dev/bin/python
import lsdb1
import sys
import logging
logger = logging.getLogger(__name__)

startDate = sys.argv[1]
endDate = sys.argv[2]
beamline = sys.argv[3]

#lsdb1.printColRequestsByTimeInterval('2017-10-11T00:00:00','2017-10-13T00:00:00',"johnSweep.txt")

m = lsdb1.getMountCount(startDate,endDate,beamline)
logger.info(m)

