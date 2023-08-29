import logging
import os
from collections import deque
import getpass
import grp
from ophyd.sim import NullStatus
from ophyd.status import SubscriptionStatus

logger = logging.getLogger(__name__)

DEFAULT_DATUM_DICT = {"data": None, "omega": None}

INTERNAL_SERIES = 0
INTERNAL_ENABLE = 1
EXTERNAL_SERIES = 2
EXTERNAL_ENABLE = 3

class MD2StandardFlyer():
    def __init__(self, md2, detector=None) -> None:
        self.name = "MD2Flyer"
        self.detector = detector
        self.md2 = md2
        self.collection_params = {}

        self._asset_docs_cache = deque()
        self._resource_uids = []
        self._datum_counter = None
        self._datum_ids = DEFAULT_DATUM_DICT
        self._master_file = None
        self._master_metadata = []

        self._collection_dictionary = None

    def kickoff(self):
        self.md2.standard_scan(num_images=self.collection_params["total_num_images"],
                               start_angle=self.collection_params["start_angle"],
                               scan_range=self.collection_params["img_width"],
                               exposure_time=self.collection_params["exposure_per_image"])
        return NullStatus()

    def update_parameters(self, angle_start, img_width, total_num_images, exposure_per_image):
        self.collection_params = {
            "angle_start": angle_start,
            "img_width": img_width,
            "total_num_images": total_num_images,
            "exposure_per_image": exposure_per_image,
        }
        
    def configure_detector(self, *args, **kwargs):
        file_prefix = kwargs["file_prefix"]
        data_directory_name = kwargs["data_directory_name"]
        self.detector.file.external_name.put(file_prefix, wait=True)
        self.detector.file.write_path_template = data_directory_name

    def detector_arm(self, angle_start, img_width, total_num_images, exposure_per_image, 
                     file_prefix, data_directory_name, file_number_start, x_beam, y_beam, 
                     wavelength, det_distance_m, num_images_per_file):
        self.detector.cam.save_files.put(1)
        self.detector.cam.file_owner.put(getpass.getuser())
        self.detector.cam.file_owner_grp.put(grp.getgrgid(os.getgid())[0])
        self.detector.cam.file_perms.put(420)
        file_prefix_minus_directory = str(file_prefix)
        file_prefix_minus_directory = file_prefix_minus_directory.split("/")[-1]
        self.detector.cam.acquire_time.put(exposure_per_image)
        self.detector.cam.acquire_period.put(exposure_per_image)
        self.detector.cam.num_triggers.put(total_num_images)
        self.detector.cam.file_path.put(data_directory_name, wait=True)
        self.detector.cam.fw_name_pattern.put(f"{file_prefix_minus_directory}_$id", wait=True)
        self.detector.cam.sequence_id.put(file_number_start, wait=True)
        self.detector.cam.beam_center_x.put(x_beam)
        self.detector.cam.beam_center_y.put(y_beam)
        self.detector.cam.omega_incr.put(img_width)
        self.detector.cam.omega_start.put(angle_start)
        self.detector.cam.wavelength.put(wavelength)
        self.detector.cam.det_distance.put(det_distance_m)
        self.detector.cam.trigger_mode.put(
            EXTERNAL_ENABLE
        )  # must be external_enable to get the correct number of triggers and stop acquire
        self.detector.file.file_write_images_per_file.put(num_images_per_file, wait=True)

        def armed_callback(value, old_value, **kwargs):
            if old_value == 0 and value == 1:
                return True
            return False

        status = SubscriptionStatus(self.detector.cam.armed, armed_callback, run=False)
        self.detector.cam.acquire.put(1)
        yield status

    def complete(self):
        # monitor md2 status, wait for ready or timeout and then return
        ready_status = self.md2.ready_status()
        ready_status.wait(timeout=20)
        return ready_status

    def describe_collect(self):
        return {"stream_name": {}}
        #return {self.name: self._collection_dictionary}

    def collect(self):
        logger.debug("raster_flyer.collect(): going to unstage now")
        yield {"data": {}, "timestamps": {}, "time": 0, "seq_num": 0}
        #return self._collection_dictionary

    def unstage(self):
        logger.debug("flyer unstaging")
        self.collection_params = {}

    def collect_asset_docs(self):
        for _ in ():
            yield _