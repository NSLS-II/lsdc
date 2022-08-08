============================
Processing Node Installation
============================

--------------
Pre-requisites
--------------

1. The most recent RHEL should be installed
2. The following directories should be visible:

   - /nsls2/software/mx/daq
   - /nsls2/data/<tla> where <tla> = three-letter acronym for beamline (amx/fmx/nyx)

---------
Procedure
---------

Use the "Schedule Remote Job" item in Explorer for the selected host(s) to run the following roles:

 - Conda/"Conda - Install custom conda env (lsdc-processing)"
 - Miscellaneous/"mx_software"
