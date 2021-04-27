#!/bin/bash -l
export PROJDIR=/GPFS/CENTRAL/xf17id1/skinnerProjectsBackup/
export CONFIGDIR=${PROJDIR}bnlpx_config/
export LSDCHOME=${PROJDIR}lsdc
export PYTHONPATH=".:${CONFIGDIR}:/usr/local/edna-mx/mxv1/src:/usr/local/edna-mx/kernel/src:${LSDCHOME}:${PROJDIR}/RobotControlMerge"
export PATH=/usr/local/bin:/usr/bin:/bin:${PROJDIR}/software/bin:/GPFS/CENTRAL/XF17ID1/usr/local/crys/ccp4-6.5/bin
source ${CONFIGDIR}daq_env.txt
export matlab_distrib=${PROJDIR}/software/c3d/matlab_distrib
export LD_LIBRARY_PATH=$matlab_distrib/bin/glnx86:$matlab_distrib/toolbox
export PINALIGNDIR=${PROJDIR}pinAlign/pin_align-master
$LSDCHOME/lsdcServer
