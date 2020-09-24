#!/opt/conda_envs/collection-2018-1.0/bin/python
import sys
import os

fname1 = sys.argv[1]
fname2 = sys.argv[2]
pinAlignRootEnvVar = "/GPFS/CENTRAL/xf17id1/skinnerProjectsBackup/pinAlign/pin_align-master"
baseDirectory = os.environ["PWD"]
beamline = os.environ["BEAMLINE_ID"]
runningDir = baseDirectory + "/pinAlign"
os.chdir(runningDir)
comm_s = pinAlignRootEnvVar + "/pin_align_" + beamline + ".sh " + \
    fname1 + " " + fname2
lines = os.popen(comm_s).readlines()
tilted = False
for outputline in lines:
    if (outputline.find("TILTED") != -1 or outputline.find('MISSING') != -1):
        print(outputline)
        tilted = True
if (not tilted):
    for outputline in lines:
        if (outputline.find("OVERALL X,Y,Z OFFSETS TO CENTER") != -1):
            index_s = outputline.find("[")
            substring = outputline[index_s + 1:len(outputline) - 3]
            offsetTokens = substring.split(',')
            print(offsetTokens[0] + " " +
                  offsetTokens[1] + " " + offsetTokens[2])
            break
