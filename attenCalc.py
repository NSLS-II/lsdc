#   Routine to set attenuator foils for the RI attenuator, with setup imports and a testing program.
#

import logging
from math import *

import numpy as np
from pylab import *

logger = logging.getLogger(__name__)

###  RIfoils testing script
###
##outlist = []
# Energy of the photons
#etarget = 15000
# Amount of transmission the user wants: 1.0 = full beam; 0.01 = 1% of full beam.
##trans = .44
##outlist = RIfoils(etarget, trans)
##logger.info 'return from foils'
##logger.info 'Outlist:', outlist


def RIfoils(etarget,trans):
#
#  Routine to check which combination of the RI attenuators will provide the requred attenuation
#    and then insert the attenuators.
#
# The main routine will come in with these two numbers from the user:
# Energy of the photons
#  etarget = 8100  
# Amount of transmission the user wants: 1.0 = full beam; 0.01 = 1% of full beam.
#  trans = 0.026
#
# Then we'll see what thickness is requred
#
  RIthick = [0.0006, 0.00125, 0.0025, 0.005, 0.01, 0.02, 0.038, 0.08, 0.15, 0.305, 0.6, 1.2 ]
  RItotal = 2.41235
  elist = [5000, 5200, 5400, 5600, 5800, 6000, 6200, 6400, 6600, 6800, 7000, 7200, 7400, 7600, 7800, 8000, 8200, 8400, 8600, 8800, 9000, 
           9200, 9400, 9600, 9800, 10000, 10200, 10400, 10600, 10800, 11000, 11200, 11400, 11600, 11800, 12000, 12200, 12400, 12600, 
           12800, 13000, 13200, 13400, 13600, 13800, 14000, 14200, 14400, 14600, 14800, 15000, 15200, 15400, 15600, 15800, 16000, 16200, 
           16400, 16600, 16800, 17000, 17200, 17400, 17600, 17800, 18000, 18200, 18400, 18600, 18800, 19000, 19200, 19400, 19600, 19800, 
           20000, 20200, 20400, 20600, 20800, 21000, 21200, 21400, 21600, 21800, 22000, 22200, 22400, 22600, 22800, 23000, 23200, 23400, 
           23600, 23800, 24000, 24200, 24400, 24600, 24800, 25000, 25200, 25400, 25600, 25800, 26000, 26200, 26400, 
           26600, 26800, 27000, 27200, 27400, 27600, 27800, 28000, 28200, 28400, 28600, 28800, 29000, 29200, 29400, 29600, 29800, 30000]
  Almu = [520.740,465.387,417.586,376.081,339.897,308.179,280.284,255.636,233.792,214.356,197.010,181.479,167.533,154.977,143.639,133.380,
          124.071,115.603,107.888,100.842,94.395,88.481,83.053,78.059,73.454,69.205,65.277,61.637,58.265,55.131,52.219,49.507,46.978,
          44.619,42.416,40.355,38.425,36.616,34.918,33.324,31.825,30.416,29.087,27.835,26.654,25.539,24.485,23.489,22.546,21.654,20.808,
          20.003,19.241,18.517,17.829,17.174,16.552,15.960,15.395,14.857,14.343,13.854,13.387,12.941,12.513,12.105,11.715,11.343,10.984,
          10.642,10.314,9.999,9.697,9.408,9.130,8.862,8.604,8.358,8.121,7.893,7.674,7.463,7.261,7.066,6.879,6.697,6.523,6.355,6.193,6.037,
          5.886,5.740,5.600,5.465,5.334,5.208,5.085,4.966,4.852,4.742,4.634,4.532,4.431,4.334,4.240,4.149,4.060,3.975,3.892,3.812,3.735,
          3.658,3.586,3.514,3.445,3.378,3.313,3.250,3.189,3.129,3.070,3.014,2.960,2.906,2.854,2.804]
  if etarget < elist[0]: 
    logger.info("Energy is below 5 keV minimum")
    return
  elif etarget > elist[len(elist)-1]:
    logger.info('Energy is above 30 keV maximum')
    return
#  
  outlist = []
  logger.info("Photon Energy:", etarget)
  mutarget = np.interp(etarget, elist, Almu, left=None, right=None, period=None)
  logger.info('mu-target: ', mutarget)
#
  logger.info("Transmission:", trans)
  thick = log(trans) / (-1.0*mutarget)
  fraction = thick / RItotal
  logger.info('Thickness, Fraction:', thick, fraction)
  if fraction > 1.0:
    logger.info('This attenuator is not thick enough')
    return []
#john
  intBits = int(fraction * 4096.0)
  logger.info('Bit pattern: ', bin(intBits))
  for i in range (0,12):
    binstring = bin(intBits>>i)
    myBit = binstring[len(binstring)-1]
    outlist.append(int(myBit))
  return outlist


