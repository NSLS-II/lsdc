def gen_traj_square(x_start, x_end, y_start, y_end, z_start, z_end, col, row):
#12/19 skinner did not write this
    #   x/y/z_start/end are the definitions (in micron) of the raster area
    #   x_end - x_start should be positive
    #   step defines the step size of the raster and should be positive
    import numpy as np
    # import matplotlib.pyplot as plt

    # ==========================================================================
    # may need a few lines of code to center the (0,0,0) of the piezo stage to
    # the center of the raster area
    # ==========================================================================

    x = x_end-x_start
    # If the X size of the raster area is larger than 180 micron, return an error message
    if np.abs(x) > 180:
        print('x range error')
        return

    y = y_end-y_start
    z = z_end-z_start
    # If the Y size of the raster area is larger than 150 micron, return an error message
    if np.abs(y) > 150:
        print('y range error')
        return

    # If the Z size of the raster area is larger than 150 micron, return an error message
    if np.abs(z) > 150:
        print('z range error')
        return

    step = x / col
    d = np.sqrt(y * y + z * z)
    delta_y = y/(row-1)
    delta_z = z/(row-1)
    # cycles = np.round(d/step)                       # calculate the number of line scans for the raster
    # cycles = np.int(np.floor(cycles))
    # if np.remainder(cycles, 2) == 0:                # make sure the number of cycles is odd
    #    cycles = cycles + 1

    x_traj_odd = np.arange(x_start, x_end, step)            # x positions of the odd line
    x_traj_even = np.arange(x_end, x_start, -step)          # x positions of the even line
    y_traj_unit = np.zeros(x_traj_odd.size) + y_start       # y positions of the first line
    z_traj_unit = np.zeros(x_traj_odd.size) + z_start       # z positions of the first line

    x_traj = x_traj_odd         # first line of the x
    y_traj = y_traj_unit        # first line of the y
    z_traj = z_traj_unit        # first line of the z
    for i in range(np.int(row-1)):
        if np.remainder(i, 2) == 0:                     # add (x,y,z) positions for the even lines
            x_traj = np.append(x_traj, x_traj_even)
            y_traj = np.append(y_traj, y_traj_unit + delta_y * (i+1))
            z_traj = np.append(z_traj, z_traj_unit + delta_z * (i+1))
        if np.remainder(i, 2) == 1:                     # add (x,y,z) positions for the odd lines
            x_traj = np.append(x_traj, x_traj_odd)
            y_traj = np.append(y_traj, y_traj_unit + delta_y * (i+1))
            z_traj = np.append(z_traj, z_traj_unit + delta_z * (i+1))

    Traj = np.append([x_traj], [y_traj], 0)
    Traj = np.append(Traj, [z_traj], 0)
    return Traj
