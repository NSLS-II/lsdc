import os
import datetime
from pwd import getpwnam

def get_visit_info(entry):
    split_name = entry.split()
    prop_type = split_name[0]
    prop_number = split_name[1][:6]
    remote = prop_number.endswith('(R)')
    return {'prop_type':prop_type, 'prop_number':prop_number, 'remote':remote}

def get_directory_name(central_storage_prefix, beamline_prefix, prop_type, prop_number, remote):
    #defined as 2 or 3 letters (RA GU BAG PR DT), 6 digits. remote
    prop_number = int(prop_number)
    visit_date = datetime.date.today().strftime('%d%b%Y')
    if remote:
        remote_text = 'Remote_' # underscore to space from visit_date
    else:
        remote_text = ''
    shortest_dir_name = f"{prop_type.upper()}-{prop_number}_{remote_text}{visit_date}"
    short_dir_name = f"{beamline_prefix}/{shortest_dir_name}"
    dir_name = f"{central_storage_prefix}/{short_dir_name}"
    return dir_name, short_dir_name, shortest_dir_name

#mode must be an octal literal - 0o??? where ??? are octal digits
#owner - if empty, use current user. if running as sudo and owner is specified, change owner to that user
def make_directory(directory_name, mode=0o755, owner=''):
    os.makedirs(directory_name, mode=mode)
    if len(owner)>1:
        owner_uid = getpwnam(owner).pw_uid
        owner_gid = getpwnam(owner).pw_gid
        os.chown(directory_name, owner_uid, owner_gid)

def send_globus_email(email_list, endpoint):
    from_email = '' #

#def test_make_directory('juntest')#, owner='jaishima')
