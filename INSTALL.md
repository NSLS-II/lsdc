Note: the following directions should be current as of 2021-04-07. RHEL 8 operating system is being used.
== Conda environments for the GUI and server ==

* https://github.com/JunAishima/epicsPython
* Dectris Albula - get the download from www.dectris.com - registration required
* If necessary, modify the ipython and pythons used in the first lines (hash-bang) to match where the server and GUI are located

== Other configuration and code for LSDC

* Dectris Albula - get the download from www.dectris.com - registration required
  * install using the appropriate packing system
* https://github.com/NSLS-II/RobotControlLib.git
* https://github.com/pelirrojo725/pin_align-master - use main branch
* https://github.com/NSLS-II/mx-processing-wrappers - EDNA and fast DP wrappers
* https://github.com/NSLS-II/lsdc_bnlpx_config

== Procedure to set things up ==

* copy the lsdcGui and lsdcServer scripts from bin to your /usr/local/bin directory or whatever is on your $PATH so that it can be executed
* in lsdcServer.cmd, modify the locations of $PROJDIR, $CONFIGDIR (lsdc_bnlpx_config), $LSDCHOME (this library)
* in lsdcGui, modify PYTHONPATH for albula library location (usually /opt/dectris/albula/4.0/python) and EDNA, $LSDCHOME (this library), and $CONFIGDIR (bnlpx_config)
* modify bnlpx_config files epx.db and daq_env.txt (or whatever you point to from lsdcGui and lsdcServer) so that they reflect the correct PVs and environment, respectively, for your local system
* make sure that all of your EPICS PVs are available on the computers where you are running lsdcGui and lsdcServer!
== TODO ==

* make the package installable with pip - get a working setup.py - will probably require splitting into common, server, and GUI packages of which server and GUI can be installed separately
* make the startup scripts daq_main2, daq_mainAux, lsdcGui use better ways to define the Python they will use
