#!/bin/bash -l
export PROJDIR=/GPFS/CENTRAL/xf17id2/skinnerProjectsBackup/
export CONFIGDIR=${PROJDIR}bnlpx_config/
export LSDCHOME=${PROJDIR}lsdc
export PYTHONPATH=".:${CONFIGDIR}:/usr/local/edna-mx/mxv1/src:/usr/local/edna-mx/kernel/src:${LSDCHOME}:${PROJDIR}/RobotControlMerge"
export PATH=/usr/local/bin:/usr/bin:/bin:${PROJDIR}/software/bin:/opt/ccp4/bin
source ${CONFIGDIR}daq_env.txt
export matlab_distrib=${PROJDIR}/software/c3d/matlab_distrib
export LD_LIBRARY_PATH=$matlab_distrib/bin/glnx86:$matlab_distrib/toolbox
export PINALIGNDIR=${PROJDIR}pinAlign/pin_align-master/
export MXPROCESSINGSCRIPTSDIR=${PROJDIR}mx-processing/
export WRAPPERSDIR=${PROJDIR}wrappers/
# below not idea as environment name also needed by daq_main2
conda activate lsdc-server-2021-1.3
export KAFKA_SERVERS="kafka1.nsls2.bnl.gov:9092,kafka2.nsls2.bnl.gov:9092,kafka3.nsls2.bnl.gov:9092,kafka4.nsls2.bnl.gov:9092,kafka5.nsls2.bnl.gov:9092,kafka6.nsls2.bnl.gov:9092,kafka7.nsls2.bnl.gov:9092"
$LSDCHOME/lsdcServer
