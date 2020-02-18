import numpy as np
import epics
import logging
logger = logging.getLogger(__name__)

#12/19 - skinner did not write this.
def gen_commands(traj,exptime):

    # The traj is a 3 x N array which contains the (x,y,z) positions of the trajectory
    # The purpose of this function is generating three lists (for x, y, z, repectively).
    # Each list contains a series of "WAV ... " commands to write

    size = traj.shape

    if size[0] != 3:
        size = traj.transpose().shape

    commands = [
        'WGC 0 1',
        'STP',
        'WTR 0 %d 1'% (exptime*20000,)
    ]
    
    for j in range(3):
        commands.append('WOS %d 0' % (j+1,))
        for i in range(int(np.floor(size[1]/2))):
            SegLength = 2
            StartPoint = 0
            Amp = traj[j][i*2+1] - traj[j][i*2]
            Offset = traj[j][i*2]
            WaveLength = SegLength
            SpeedUpDown = 0
            Replace = 'X' if i == 0 else '&'
            commands.append("WAV %d %s LIN %d %.3f %.3f %d %d %d" % (j+1, Replace, SegLength, Amp, Offset, WaveLength, StartPoint, SpeedUpDown))
        commands.append('WSL %d %d' % (j+1,j+1))
    
    oeos = epics.PV('XF:17IDC-CT:FMX{MC:21}Asyn.OEOS')
    aout = epics.PV('XF:17IDC-CT:FMX{MC:21}Asyn.AOUT')
    tmod = epics.PV('XF:17IDC-CT:FMX{MC:21}Asyn.TMOD')

    tmod.put('Write')
    oeos.put('\n')
    
    for cmd in commands:
#        logger.info(len(cmd),cmd)
        aout.put(cmd, wait=True)

    tmod.put('Write/Read')

def go_all():
    aout = epics.PV('XF:17IDC-CT:FMX{MC:21}Asyn.AOUT')
    tmod = epics.PV('XF:17IDC-CT:FMX{MC:21}Asyn.TMOD')

    tmod.put('Write')
    for n in range(1, 4):
        logger.info("Arming waveform", n)
        aout.put('WGO %d 0x102' % (n,), wait=True)
        
    tmod.put('Write/Read')

