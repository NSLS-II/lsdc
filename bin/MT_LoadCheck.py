# -*- coding: utf-8 -*-
"""
Created on Mon Aug 29 10:37:32 2016

@author: kun
"""

import robot as rob
import time

CMD_TIMEOUT = 500000


try:

    cmds=['Initialize','Cooldown']
    for scmd in cmds:
        tskStat, sampleStat, exception = rob.runATask(scmd, CMD_TIMEOUT)
        if (tskStat.lower()!="done"):
            raise Exception(scmd+" "+tskStat+" with exception "+exception)

    cmds=['MT_loadCheck']
    for i in range(1,2):
        print( "================================== Plate",i, "=================================")

        for n in range(1,49):
            rob.par.execute("nSample",n)
            rob.parChk.execute("nDummy")
            if n!=int(float(rob.parChk.execute("nSample"))):
                raise Exception("Failed to set robot viable nSample")

#            if n in [17,33]:
#		rob.runATask("Cooldown", CMD_TIMEOUT)

            for scmd in cmds:
                tskStat, sampleStat, exception = rob.runATask(scmd, CMD_TIMEOUT)
                if (tskStat.lower()!="done" and not tskStat.startswith("Done")):
                    raise Exception(scmd+" "+tskStat+" with exception "+exception)


    #rob.runATask("TraceSample", CMD_TIMEOUT)

finally:
    rob.runATask("TraceSample", CMD_TIMEOUT)
    rob.runATask("Finish", CMD_TIMEOUT)
