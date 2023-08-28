from ophyd import Device, Component as Cpt, EpicsSignal, EpicsSignalRO, PVPositioner

class MD2Positioner(PVPositioner):
    setpoint = Cpt(EpicsSignal, 'Position', name='setpoint')
    readback = Cpt(EpicsSignal, 'Position', name='readback')
    state = Cpt(EpicsSignalRO, 'State', name='state')
    done = Cpt(EpicsSignalRO, 'State', name='done')
    precision = Cpt(EpicsSignalRO, 'Precision', name='precision')
    done_value = 4 # MD2 Enum, 4 = Ready
    # TODO: Add limits, settle_time, timeout or defaults for each

    def val(self):
        return self.get().readback

class FrontLightDevice(Device):
    control = Cpt(EpicsSignal, 'FrontLightIsOn', name='control')
    factor = Cpt(EpicsSignal, 'FrontLightFactor', name='factor')
    level = Cpt(EpicsSignal, 'FrontLightLevel', name='level')
    
    def is_on(self):
        return self.control.get() == 1

    def turn_on(self):
        self.control.set(1)

    def turn_off(self):
        self.control.set(0)

    def set_factor(self, factor):
        self.factor.set(factor)
    
    def set_level(self, level):
        self.level.set(level)

class BeamstopDevice(Device):
    distance = Cpt(MD2Positioner, "BeamstopDistance", name="distance")
    x = Cpt(MD2Positioner, "BeamstopX", name="x")
    y = Cpt(MD2Positioner, "BeamstopY", name="y")
    z = Cpt(MD2Positioner, "BeamstopZ", name="z")
    position = Cpt(EpicsSignal, "BeamstopPosition", name="position")

class MD2SimpleHVDevice(Device):
    horizontal = Cpt(MD2Positioner, "HVHorizontal", name="horizontal")
    vertical = Cpt(MD2Positioner, "HVVertical", name="vertical")
    position = Cpt(EpicsSignal, "HVPosition", name="position")
    # Current aperture/scintillator/capillary predifined position.
    # Enum: the aperture position:
    # 0: PARK, under cover.
    # 1: BEAM, selected aperture aligned with beam.
    # 2: OFF, just below the OAV.
    # 3: UNKNOWN, not in a predefined position (this cannot be set).

class GonioDevice(Device):
    omega = Cpt(MD2Positioner, 'Omega',name='omega')
    x = Cpt(MD2Positioner, 'AlignmentX',name='x')
    y = Cpt(MD2Positioner, 'AlignmentY',name='y')
    z = Cpt(MD2Positioner, 'AlignmentZ',name='z')

class MD2Device(GonioDevice):
    cx = Cpt(MD2Positioner, 'CentringX',name='cx')
    cy = Cpt(MD2Positioner, 'CentringY',name='cy')
    phase_index = Cpt(EpicsSignalRO, 'CurrentPhaseIndex',name='phase_index')
    detector_state = Cpt(EpicsSignal, 'DetectorState',name='det_state')
    detector_gate_pulse_enabled = Cpt(EpicsSignal, 'DetectorGatePulseEnabled',name='det_gate_pulse_enabled')

    def standard_scan(self, 
            frame_number=0, # int: frame ID just for logging purposes.
            num_images=1, # int: number of frames. Needed solely when the detector use gate enabled trigger.
            start_angle=0, # double: angle (deg) at which the shutter opens and omega speed is stable.
            scan_range=1, # double: omega relative move angle (deg) before closing the shutter.
            exposure_time=0.1, # double: exposure time (sec) to control shutter command.
            num_passes=1 # int: number of moves forward and reverse between start angle and stop angle
            ):
        command = 'startScanEx2'
        if start_angle is None:
            start_angle=self.omega.get()
        return self.exporter.cmd(command, [frame_number, num_images, start_angle, scan_range, exposure_time, num_passes])

    def vector_scan(self,
            start_angle=None, # double: angle (deg) at which the shutter opens and omega speed is stable.
            scan_range=10, # double: omega relative move angle (deg) before closing the shutter.
            exposure_time=1, # double: exposure time (sec) to control shutter command.
            start_y=None, # double: PhiY axis position at the beginning of the exposure.
            start_z=None, # double: PhiZ axis position at the beginning of the exposure.
            start_cx=None, # double: CentringX axis position at the beginning of the exposure.
            start_cy=None, # double: CentringY axis position at the beginning of the exposure.
            stop_y=None, # double: PhiY axis position at the end of the exposure.
            stop_z=None, # double: PhiZ axis position at the end of the exposure.
            stop_cx=None, # double: CentringX axis position at the end of the exposure.
            stop_cy=None, # double: CentringY axis position at the end of the exposure.
            ):
        command = 'startScan4DEx'
        if start_angle is None:
            start_angle = self.omega.val()
        if start_y is None:
            start_y = self.y.val()
        if start_z is None:
            start_z = self.z.val()
        if start_cx is None:
            start_cx = self.cx.val()
        if start_cy is None:
            start_cy = self.cy.val()
        if stop_y is None:
            stop_y = self.y.val()+0.1
        if stop_z is None:
            stop_z = self.z.val()+0.1
        if stop_cx is None:
            stop_cx = self.cx.val()+0.1
        if stop_cy is None:
            stop_cy = self.cy.val()+0.1

        # List of scan parameters values, comma separated. The axes start values define the beginning
        # of the exposure, that is when all the axes have a steady speed and when the shutter/detector
        # are triggered.
        # The axes stop values are for the end of detector exposure and define the position at the
        # beginning of the deceleration.
        # Inputs names: "start_angle", "scan_range", "exposure_time", "start_y", "start_z", "start_cx",
        # "start_cy", "stop_y", "stop_z", "stop_cx", "stop_cy"
        param_list = [start_angle, scan_range, exposure_time,
                start_y, start_z, start_cx, start_cy, 
                stop_y, stop_z, stop_cx, stop_cy]
        return self.exporter.cmd(command, param_list)

    def raster_scan(self, 
            omega_range=0, # double: omega relative move angle (deg) before closing the shutter.
            line_range=0.1, # double: horizontal range of the grid (mm).
            total_uturn_range=0.1, # double: vertical range of the grid (mm).
            start_omega=None, # double: angle (deg) at which the shutter opens and omega speed is stable.
            start_y=None, # double: PhiY axis position at the beginning of the exposure.
            start_z=None, # double: PhiZ axis position at the beginning of the exposure.
            start_cx=None, # double: CentringX axis position at the beginning of the exposure.
            start_cy=None, # double: CentringY axis position at the beginning of the exposure.
            number_of_lines=5, # int: number of frames on the vertical range.
            frames_per_line=5, # int: number of frames on the horizontal range.
            exposure_time=1.2, # double: exposure time (sec) to control shutter command. +1, based on the exaples given
            invert_direction=True, # boolean: true to enable passes in the reverse direction.
            use_table_centering=True, # boolean: true to use the centring table to do the pitch movements.
            use_fast_mesh_scans=True # boolean: true to use the fast raster scan if available (power PMAC).
            ):

        command = 'startRasterScanEx'
        if start_omega is None:
            start_omega = self.omega.val()
        if start_y is None:
            start_y = self.y.val()
        if start_z is None:
            start_z = self.z.val()
        if start_cx is None:
            start_cx = self.cx.val()
        if start_cy is None:
            start_cy = self.cy.val()
        # List of scan parameters values, "/t" separated. The axes start values define the beginning
        # of the exposure, that is when all the axes have a steady speed and when the shutter/detector
        # are triggered.
        # The axes stop values are for the end of detector exposure and define the position at the
        # beginning of the deceleration.
        # Inputs names: "omega_range", "line_range", "total_uturn_range", "start_omega", "start_y",
        # "start_z", "start_cx", "start_cy", "number_of_lines", "frames_per_lines", "exposure_time",
        # "invert_direction", "use_centring_table", "use_fast_mesh_scans"
        param_list = [omega_range, line_range, total_uturn_range, start_omega, start_y, start_z,
                start_cx, start_cy, number_of_lines, frames_per_line, exposure_time, 
                invert_direction, use_table_centering, use_fast_mesh_scans]
        return self.exporter.cmd(command, param_list)

class ShutterDevice(Device):
    control = Cpt(EpicsSignal, '{MD2}:FastShutterIsOpen', name='control') # PV to send control signal
    pos_opn = Cpt(EpicsSignalRO, '{Gon:1-Sht}Pos:Opn-I', name='pos_opn')
    pos_cls = Cpt(EpicsSignalRO, '{Gon:1-Sht}Pos:Cls-I', name='pos_cls')

    def is_open(self):
        return self.control.get() == 1 #self.pos_opn.get()

    def open_shutter(self):
        self.control.set(1)#self.pos_opn.get()) iocs are down, so just setting it to 1

    def close_shutter(self):
        self.control.set(0)#self.pos_cls.get())