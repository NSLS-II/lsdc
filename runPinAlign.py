#!/opt/conda_envs/lsdc-server-2022-3.1/bin/python
import sys
import os

fname1 = sys.argv[1]
fname2 = sys.argv[2]
pinAlignDir = os.environ['PINALIGNDIR']
baseDirectory = os.environ["PWD"]
beamline = os.environ["BEAMLINE_ID"]
runningDir = baseDirectory + "/pinAlign"
os.chdir(runningDir)
scriptName = os.path.join(pinAlignDir, f'pin_align_{beamline}.sh')
comm_s = f'{scriptName} {fname1} {fname2}'
lines = os.popen(comm_s).readlines()
tilted = False

##### TODO add check for high values
for outputline in lines:
    if (outputline.find("TILTED") != -1 or outputline.find('MISSING') != -1 or outputline.find('VIOLATION') != -1):
        print(outputline)
        tilted = True
        sys.exit()
if (not tilted):
    for outputline in lines:
        try:
            if (outputline.find("OVERALL X,Y,Z OFFSETS TO CENTER") != -1):
                index_s = outputline.find("[")
                substring = outputline[index_s + 1:len(outputline) - 3]
                offsetTokens = substring.split(',')
                print(offsetTokens[0] + " " +
                      offsetTokens[1] + " " + offsetTokens[2])
                sys.exit()
        except Exception:
            print('Top-view error, pin could be out of view, manual centering required')


