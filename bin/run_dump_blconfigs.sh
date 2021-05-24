#!/bin/bash
conda activate lsdcServer_2020-1.0
python dump_blconfigs.py
mv blconfig* /GPFS/CENTRAL/xf17id1/skinnerProjectsBackup/bnlpx_config/blConfigs
