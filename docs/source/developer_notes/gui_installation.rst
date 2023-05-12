=================================
LSDC Gui Installation
=================================
Steps
-----

1. make sym-links for startup scripts
..
::
    which lsdcGui
    # if this is a valid path stop here
    
    cd /usr/local/bin
    dzdo ln -s /nsls2/software/mx/daq/lsdc_nyx/bin/lsdcGui_nyx lsdcGui

2. install custom gui conda environment
..
::
    explorer.nsls2.bnl.gov/job_templates
    "Conda - Install custom conda env (lsdc-gui)"
    "Actions" column > press Run
    on "Job invocation" page > enter host name into "Search Query" 
                             > "Resolves to" row > Click Refresh
                             # "Resolves to" row should now say "1 hosts"
                             > press Submit
    on "Overview" page > should say "0% pending"
                       > wait for "100% success"
                       # if it fails, click on the hosts name at the bottom of the page
                       # page will show additional information for staff

3. make sym-links for conda environment current version to latest
..
:: 
    dzdo ln -s /opt/conda_envs/lsdc-gui-year-x.y /opt/conda_envs/lsdc-gui-year-x-latest
4. install albula
..
::
    which albula
    # if it returns /usr/bin/albula this step has been completed
    
    explorer.nsls2.bnl.gov/job_templates
    "mx_software"
    "Actions" column > press Run
    on "Job invocation" page > enter host name into "Search Query" 
                             > "Resolves to" row > Click Refresh
                             # "Resolves to" row should now say "1 hosts"
                             > press Submit
    on "Overview" page > should say "0% pending"
                       > wait for "100% success"
                       # if it fails, click on the hosts name at the bottom of the page
                       # page will show additional information for staff