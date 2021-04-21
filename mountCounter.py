#!/opt/conda_envs/lsdcServer_2020-1.0/bin/python
import lsdb1
import sys

startDate = sys.argv[1]
endDate = sys.argv[2]
beamline = sys.argv[3]

m = lsdb1.getMountCount(startDate,endDate,beamline)
print(m)

