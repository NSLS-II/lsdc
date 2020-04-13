#!/opt/conda_envs/user_changer/bin/python
import os
import sys
import math
import time
import datetime
import argparse
import user_changer_utils
import email.utils
import globus_user_generic

default_date = datetime.date.today().strftime('%d%b%Y')

parser = argparse.ArgumentParser(description='User change - directory creation, Globus link generation and sending')
parser.add_argument('--prop-type', help='Proposal type') #choice of several types
parser.add_argument('--prop-num', help='Proposal number') #6-digit number
parser.add_argument('--is-remote', action='store_true', help='Flag for whether visit is remote or not. do not use for local')
parser.add_argument('--date', default=default_date, help='Date of visit - format is DaMonYear such as 03Apr2020. default is today') #automatically use today
parser.add_argument('--do-it-for-real', action='store_true', help='Actually create a directory and try to get a share endpoint')
parser.add_argument('--beamline', default=os.environ['BEAMLINE_ID'], help='Name, FMX or AMX. default is to use the value in the environment variable BEAMLINE_ID') #will automatically use BEAMLINE_ID
parser.add_argument('--emails', help='Email addresses to send Globus link to, separated by commas ","')

args = parser.parse_args()

base_directory = '/GPFS/CENTRAL'
beamline_map = {'FMX':'xf17id1', 'AMX':'xf17id2'} # for directory names

options = vars(args)
beamline_folder = beamline_map[options['beamline'].upper()]

#validation
valid_prop_types = ['RA', 'GU', 'BAG', 'PR', 'DT']
if not options['prop_type']:
    raise ValueError('prop-type must be set!')
if not options['prop_type'].upper() in valid_prop_types:
    raise ValueError('prop-type is not one of the valid prop types: %s' % ','.join(valid_prop_types))
if not options['prop_num']:
    raise ValueError('prop-num must be set!')
proposal_number = int(options['prop_num'])
proposal_digits = 6
if int(math.log10(proposal_number)) + 1 != proposal_digits:
    raise ValueError('prop-num must be %s digits' % proposal_digits)
emails = options['emails'].split(',')
email_list = []
for single_email in emails:
    parsed_email = email.utils.parseaddr(single_email)
    if not '@' in parsed_email[1]:
        raise ValueError('invalid email address, does not have an "@": %s' % single_email)
    email_list.append(parsed_email[1])

#the folder part!
long_dir_name, short_dir_name = user_changer_utils.get_directory_name(base_directory, beamline_folder, options['prop_type'].upper(), proposal_number, options['is_remote'])
print('folder name: %s' % long_dir_name)
if options['do_it_for_real']:
    user_changer_utils.make_directory(long_dir_name) #mode=0x770 by default
globus_directory_name = '/~/nsls2/direct/%s' % short_dir_name
print('for globus, use the following: %s' % globus_directory_name)
print('preparing Globus endpoint and adding the following people to the endpoint: %s' % email_list)

#the Globus part!
#just in case of NFS or other issues, wait for a second before trying to create an endpoint
if options['do_it_for_real']:
    time.sleep(1)
    globus_dict = globus_user_generic.native_app_authenticate()
    nsls_ii_endpoint_id = '92212f64-44f2-11e9-9e69-0266b1fe9f9e' #NSLS-II collection
    globus_dict = globus_user_generic.create_shared_endpoint(globus_dict, nsls_ii_endpoint_id, host_path=globus_directory_name)
    #shared_endpoint_id = '2a2d449a-783d-11ea-9615-0afc9e7dd773' #only for testing!
    globus_user_generic.add_users_to_shared_endpoint(globus_dict, emails)
