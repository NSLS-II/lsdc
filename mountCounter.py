#!/opt/conda_envs/lsdc_dev/bin/python
import lsdb1
import sys
import logging
logger = logging.getLogger(__name__)

startDate = sys.argv[1]
endDate = sys.argv[2]
beamline = sys.argv[3]

m = lsdb1.getMountCount(startDate,endDate,beamline)
logger.info(m)

