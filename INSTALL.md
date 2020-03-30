== Currently requires manual creation of an environment with the following ==

* https://github.com/NSLS-II/RobotControlLib.git 
* https://github.com/NSLS-II/lsdc_bnlpx_config
* https://github.com/jskinner53/epicsPython
* Dectris Albula - get the download from www.dectris.com - registration required

== Procedure to set things up ==

* copy the lsdcGui and lsdcServer scripts from bin to your /usr/local/bin directory or whatever is on your $PATH so that it can be executed
* modify the locations of $PROJDIR, albula libraries, epicsPython libraries
* modify bnlpx_config files epx.db and daq_env.txt (or whatever you point to from lsdcGui and lsdcServer) so that they reflect the correct PVs and environment, respectively, for your local system
* make sure that all of your EPICS PVs are available on the computers where you are running lsdcGui and lsdcServer!

== TODO ==

* make the package installable with pip - get a working setup.py
* make the startup scripts daq_main2, daq_mainAux, lsdcGui use better ways to define the Python they will use
