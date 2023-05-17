import sys
import logging
from pathlib import Path
from networkx import DiGraph, bfs_tree


logger = logging.getLogger()
class bcolors:
    """Class to add colors to output text"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'



def healthcheck(name:str='', 
                remediation: str='',
                fatal=False,
                depends=None):
    """Decorator added to functions that checks the health of the system, ideally before
    running the LSDC code
    """
    def dec(f):
        f.name = name
        if not hasattr(f, remediation):
            f.remediation = remediation
        f.fatal = fatal
        f.passed = True
        f.depends = depends if depends is not None else [start]
        return f
    return dec

# Add check functions with the above decorator here...
@healthcheck(name='start', depends=())
def start():
    return True

@healthcheck(
    name='import daq_utils',
    remediation='', # Dynamic remediation defined in function
    fatal=True
)
def check_daq_utils():
    try:
        import daq_utils
        return True
    except Exception as e:
        check_daq_utils.remediation = f'Error importing daq_utils: {e}'
        return False

@healthcheck(
    name='working directory',
    remediation='', # Dynamic remediation defined in function
    fatal=True
)
def check_working_directory():
    import daq_utils
    import os
    working_dir = Path.cwd()
    home_dir = Path.home()
    if home_dir in working_dir.parents or home_dir == working_dir:
        check_working_directory.remediation = f'Please start LSDC in {daq_utils.beamline} data directory, not home directory'
        return False
    if daq_utils.beamline not in working_dir.parts: 
        # Hacky way to check if amx or fmx is in path. Unless server can tell GUI where its running?
        check_working_directory.remediation = f'Please start LSDC in {daq_utils.beamline} data directory. Current directory: {working_dir}'
        return False
    else:
        return True
    if daq_utils.getBlConfig("visitDirectory") != os.getcwd():
        check_working_directory.remediation = ("Working directory mismatch. Please start LSDC GUI in the same folder as the server is running.")
        return False
    return True


@healthcheck(
    name='database lib',
    remediation='Please check if mongo database and servers are running',
    fatal=False
)
def check_db():
    import db_lib
    return True


def handle_fail(check):
    """Function to handle a failed check
    """
    print(f'{bcolors.FAIL}Fail{bcolors.ENDC}')
    print(f'{bcolors.WARNING}{bcolors.BOLD}{check.remediation}{bcolors.ENDC}')
    check.passed = False
    logger.error(f'Check {check.name} failed')
    if check.fatal:
        print("End checks")
        print(u'\u2500' * 20)
        sys.exit('Fatal error, exiting...')
        

def perform_checks():
    """Call this function to contruct a DAG where each node is evaluated using 
    breadth first search. DAGs allow certain tests to be run only after passing 
    specific tests. For example
    """
    checks = DiGraph()
    for c in [check_daq_utils, check_working_directory, check_db]:
        for d in c.depends:
            checks.add_edge(d, c)
    print(u'\u2500' * 20)
    print("Begin checks")
    for check in bfs_tree(checks, start):
        try:
            if all([parent.passed for parent in checks.predecessors(check)]):
                print(f'Checking {check.name}...', end='\t')
                if check():
                    print(f'{bcolors.OKGREEN}Success{bcolors.ENDC}')
                else:
                    handle_fail(check)
        except Exception as e:
            print(f'Exception: {e}')
            logger.error(f'Exception during checks {e}')
            handle_fail(check)
    print("End checks")
    print(u'\u2500' * 20)
