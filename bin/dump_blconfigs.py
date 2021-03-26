import db_lib
from datetime import date
import sys

'''
Script to dump all config parameters for beamlines

Directions: copy or link this file to the top level of LSDC.
setup the main conda environment such as lsdcServer_2020-1.0.
LSDC must be in the PYTHONPATH or be local
python <this script name>
Output will be files called blconfig_params_{blname}_{date}
'''
def getConfigParamsDict(beamline_id):
    configList = db_lib.getAllBeamlineConfigParams(beamline_id)
    configDict = {}
    for config in configList:
        try:
            configDict[config['info_name']] = config['info']['val']
        except KeyError:
            pass
    return configDict

def getAllBeamlineConfigParams(beamline_id):
    configDict = getConfigParamsDict(beamline_id)
    to_return = ''
    for name, value in configDict.items():
       to_return += f'{name} {value}\n'
    return to_return

def printAllBeamlineConfigParams(beamline_id):
    print(getAllBeamlineConfigParams(beamline_id))

def logAllBeamlineConfigParams(beamline_id):
    configDict = getConfigParamsDict(beamline_id)
    for name, value in configDict.items():
        logger.info(f'{name} {value}')

if __name__ == '__main__':
    #printAllBeamlineConfigParams('amx')
    #sys.exit(0)
    for beamline_id in ['amx', 'fmx']:
        with open(f'blconfig_params_{beamline_id}_{date.today().isoformat()}', 'w') as blconfig_out:
            blconfig_out.write(getAllBeamlineConfigParams(beamline_id))
