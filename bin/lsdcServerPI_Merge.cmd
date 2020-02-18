#!/bin/bash -l
export PROJDIR=/GPFS/CENTRAL/xf17id1/skinnerProjectsBackup/
export CONFIGDIR=${PROJDIR}bnlpx_config/
#export LSDCHOME=${PROJDIR}lsdcEiger2
export LSDCHOME=${PROJDIR}lsdc
export PYTHONPATH=".:${CONFIGDIR}:${PROJDIR}epics_python_dist_2k15/GUI-Qt-PyEpics:/usr/local/dectris/albula/3.1/python:/usr/local/edna-mx/mxv1/src:/usr/local/edna-mx/kernel/src:${LSDCHOME}:${PROJDIR}/RobotControlMerge"
export PATH=/opt/conda/bin/:/usr/local/bin:/usr/bin:/bin:${PROJDIR}/software/bin:/GPFS/CENTRAL/XF17ID1/usr/local/crys/ccp4-6.5/bin
# source my nfs home bash if we can get too it
#if [ -e /nfs/skinner/.bashrc ]; then
#    . /nfs/skinner/.bashrc
#fi
source activate collection-2018-1.0
source ${CONFIGDIR}daq_env.txt
export matlab_distrib=${PROJDIR}/software/c3d/matlab_distrib
export LD_LIBRARY_PATH=$matlab_distrib/bin/glnx86:$matlab_distrib/toolbox
$LSDCHOME/lsdcServer
