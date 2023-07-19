#!/opt/conda_envs/lsdc-server-2023-2-latest/bin/python
import lsdb1
import sys

startDate = sys.argv[1]
endDate = sys.argv[2]
fname = sys.argv[3]

lsdb1.printColRequestsByTimeInterval(startDate,endDate,fname)
