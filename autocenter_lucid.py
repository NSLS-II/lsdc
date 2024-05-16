import sys

sys.path.append('/nsls2/data/nyx/legacy/Rudra/wxImageViewer/lucid3/lucid3')


#from lucid_core import find_loop
import logging
import urllib.request
from io import BytesIO
from PIL import Image
import numpy
import subprocess
import time


class AutoCollect():
    def __init__(self, md2):
        self.md2 = md2
        self.is_collected = False
        self.image_url = 'http://10.67.147.26:3908/video_feed2'
        self.delay = 1000
        self.image = self.getImageFromURL()
        self.imageSize = (640,512)
        #self.key = 'bzoom:RAW'
        #self.redis_client = redis.Redis(host='10.67.146.131', port=6379, db=0)
        self.lucid_subprocess_call = ['/nsls2/data/nyx/legacy/Rudra/wxImageViewer/lucid_environment/bin/lucid3', 'CurrentSample.jpg']
        self.raster_box_subprocess_call =['curl', '-X', 'POST', '-F', 'file=@./CurrentSample.jpg', 'http://127.0.0.1:8000/predict']
        self.immediate_comm_pv = PV(daq_utils.beamlineComm + "immediate_command_s")






        #DEFINING FUNCTIONS FOR CORRECTED CLICK TO CENTER
    def getMD2ImageXRatio(self):
        md2_img_width = daq_utils.highMagPixX
        lsdc_img_width = daq_utils.screenPixX
        return float(md2_img_width) / float(lsdc_img_width)

    def getMD2ImageYRatio(self):
        md2_img_height = daq_utils.highMagPixY
        lsdc_img_height = daq_utils.screenPixY
        return float(md2_img_height) / float(lsdc_img_height)
    
    
    def getMD2BeamCenterX(self):
        return self.md2.center_pixel_x.get() / self.getMD2ImageXRatio()
    
    
    def getMD2BeamCenterY(self):
        return self.md2.center_pixel_y.get() / self.getMD2ImageYRatio()

    def getImageFromURL(self):
        image_file = BytesIO(urllib.request.urlopen(self.image_url, timeout=self.delay/1000).read())
        sample_image = Image.open(image_file)
        numpy_image = numpy.asarray(sample_image)
        return numpy_image


    def find_center_point(self):
        self.image=self.getImageFromURL()
        Image.fromarray(self.image).save('CurrentSample.jpg')
        result = subprocess.run(self.lucid_subprocess_call, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.stderr.decode() != '':
            print("ERROR:\n{}".format(result.stderr.decode()))
            return (0,0)
        val = result.stdout.decode().split('(', 1)[1].split(')')[0].split(',')
        coord_guess = (int(val[1]), int(val[2]))
        return coord_guess



    def center_on_point(self, x_click, y_click):
        #this is only for lowest magnification (ie zoom level 1) should probably set to zoom level 1 when running auto center anyway
        
        fov = {"x":0, "y":0}
        fov["x"] = daq_utils.lowMagFOVx
        fov["y"] = daq_utils.lowMagFOVy
        current_viewangle = daq_utils.mag1ViewAngle

        #done initializing zoom1 variables
        
        
        correctedC2C_x = self.getMD2BeamCenterX() + (x_click - self.getMD2BeamCenterX() - 20)
        correctedC2C_y = self.getMD2BeamCenterY() + (y_click - self.getMD2BeamCenterY() - 40)
        #still using old python string expressions should convert to ''.format()
        comm_s = f'center_on_click({correctedC2C_x},{correctedC2C_y},{fov["x"]},{fov["y"]},source="screen",maglevel=0,viewangle={current_viewangle})'
        self.immediate_comm_pv.put(comm_s)





    def start_md2_centering(self):
        self.md2.exporter.cmd("startManualSampleCentring", "")
        logger.info('starting three click centering')


    def convert_predicted_points_to_three_click(self, x_click, y_click):
        correctedC2C_x = x_click + 5 + ((daq_utils.screenPixX/2) - self.getMD2BeamCenterX())
        correctedC2C_y = y_click - 35 + ((daq_utils.screenPixY/2) - self.getMD2BeamCenterY())
        lsdc_x = daq_utils.screenPixX
        lsdc_y = daq_utils.screenPixY
        md2_x = self.md2.center_pixel_x.get() * 2
        md2_y = self.md2.center_pixel_y.get() * 2
        scale_x = md2_x / lsdc_x
        scale_y = md2_y / lsdc_y
        correctedC2C_x = correctedC2C_x * scale_x
        correctedC2C_y = correctedC2C_y * scale_y
        return correctedC2C_x, correctedC2C_y


    def send_three_click_point(self, x_click, y_click):
        final_x, final_y = self.convert_predicted_points_to_three_click(x_click, y_click)
        self.md2.centring_click.put("{} {}".format(final_x, final_y))
    
    
    def sendLucidToMD2ThreeClick(self):
        coords = self.find_center_point()
        logger.info('sending point to 3 click center ({}, {})'.format(coords[0], coords[1]))
        self.send_three_click_point(coords[0], coords[1])

    def sendLucidToC2C(self):
        coords = self.find_center_point()
        self.center_on_point(coords[0], coords[1])


    
    def auto3click_center(self):
        #check md2 status to see if its ready for three click centering
        if self.md2.is_ready() == False:
            logger.warning('MD2 Is not ready')
            return False
        #send start md2 centering
        self.start_md2_centering()
        #sanity check to see if it started manual centering
        value_checker = self.md2.task_info.value
        if value_checker[0] != 'Manual Centring' and value_checker[3] != 'null':
            logger.warning('already finished the manual centering?')
        while self.md2.is_ready() == False:
            state = self.md2.exporter.read('OmegaState')
            if state != 'Ready':
                logger.info('waiting for motor rotation')
                #logger.warning('wait a little')
                time.sleep(0.5)
            else:
                self.sendLucidToMD2ThreeClick()
        return True

    def check_if_centered(self):
        coords = self.find_center_point()
        final_x, final_y = coords[0], coords[1]
        #final_x, final_y = self.convert_predicted_points_to_three_click(x_click, y_click)
        beam_y = self.getMD2BeamCenterY()
        beam_x = self.getMD2BeamCenterX()
        #logger.warning('beamx = {} |||| final_x = {}\n beamy = {} |||| final_y = {}'.format(beam_x,final_x,beam_y,final_y))
        x_checker = (beam_x + 30 > final_x) and (beam_x - 30 < final_x)
        y_checker = (beam_y + 30 > final_y) and (beam_y - 30 < final_y)
        logger.warning('xchecker : {}, \nychecker : {}'.format(x_checker,y_checker))
        if x_checker and y_checker:
            return True
        else:
            return False
        

    def getRasterBox(self):
        self.image=self.getImageFromURL()
        Image.fromarray(self.image).save('CurrentSample.jpg')
        result = subprocess.run(self.raster_box_subprocess_call, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if 'Connection refused' in result.stderr.decode():
            logger.warning(result.stderr.decode())
            return None
        result_dict = eval(result.stdout.decode())
        box = result_dict['pred_boxes'][0]['box']
        #returns box as x1,y1,x2,y2
        bottom_left = (box[0],box[1])
        top_right = (box[2], box[3])
        return bottom_left, top_right
    
    def center_until_centered(self):
        is_centered = False
        is_centered = self.check_if_centered()
        sanity_check = 0
        while(is_centered != True):
            self.auto3click_center()
            is_centered = self.check_if_centered()
            sanity_check = sanity_check + 1
            if sanity_check > 7:
                is_centered = True
                logger.warning('\n\n\n Could not Center (Function is centered is not returning true)\n\n')
        logger.info('took {} times to auto center'.format(sanity_check))













#THE check to see if it works
#md2 = MD2Device("XF:19IDC-ES{MD2}:", name="md2")
#auto_collecter = AutoCollect(md2)
#print(auto_collecter.find_center_point())
#daq_utils.init_environment()

'''

def make():
    md2 = MD2Device("XF:19IDC-ES{MD2}:", name="md2")
    auto_collector = AutoCollect(md2)
    return auto_collector


def center_until_centered(auto_center_device):
    is_centered = False
    is_centered = auto_center_device.check_if_centered()
    sanity_check = 0
    while(is_centered != True):
        auto_center_device.auto3click_center()
        is_centered = auto_center_device.check_if_centered()
        sanity_check = sanity_check + 1
        if sanity_check > 7:
            is_centered = True
            logger.warning('\n\n\n Could not Center (Function is centered is not returning true)\n\n')
    logger.info('took {} times to auto center'.format(sanity_check))



if __name__ == '__main__':
    md2 = MD2Device("XF:19IDC-ES{MD2}:", name="md2")
    ac = AutoCollect(md2)
    center_until_centered(ac)
    print(ac.getRasterBox())

'''