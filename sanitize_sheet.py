import re
import math

valid_length = 25
valid_filename_chars = '[0-9a-zA-Z-_]{0,%s}' % valid_length
valid_chars_re = re.compile(valid_filename_chars)
valid_seq_file_re = re.compile('[0-9a-zA-Z-_]{0,%s}\.?[0-9a-zA-Z]{0,3}' % valid_length)
def print_all_errors(all_errors):
    to_return = "the following errors were found:\n"
    for error in all_errors:
        to_return.append('%s\n' % (error))
    raise Exception(to_return)

def check_sampleNames(sampleNames):
    #check for length
    valid_sampleName_chars = '[0-9a-zA-Z-_]{0,%s}' % (valid_length)
    for sampleName in sampleNames:
        #check for anything besides letters, numbers, '-', '_' and length
        if not valid_chars_re.fullmatch(sampleName):
            raise Exception('invalid characters or bad length of samplename "%s". only up to %s numbers, letters, dash ("-"), and underscore ("_") are allowed' % (sampleName, valid_length))

def create_containers():
    pass
def add_samples():
    pass
def check_for_sequence(sequence_entry):
    #length must be less than valid_length
    #if valid amino acids, then create a file and store it!
    #must be standard amino acids
    #otherwise, it should be a valid filename. shouldn't this allow one "." for extension as well?
    valid_amino_acid_chars = '[ACDEFGHIKLMNPQRSTVWY]'
    for sequence in sequence_entry:
        if not math.isnan(sequence):
            if not re.match(valid_amino_acid_chars, sequence):
                # must be a filename
                if not valid_seq_file_re.fullmatch(sequence):
                    raise Exception('invalid filename for sequence "%s".' % (sequence))
            else:
                raise Exception('sequence should not be directly entered into filename entry!')

def check_proposalNum(proposalNums):
    all_errors = []
    try:
        for proposalNum in proposalNums:
            int(proposalNum)
    except ValueError:
        raise Exception('proposal number "%s" must be a number! cannot contain letters' % proposalNum)
    proposals = set()
    for proposalNum in proposalNums:
    	proposals.add(proposalNum)
    if len(proposals) > 1:
        raise Exception('there cannot be multiple proposal numbers in spreadsheet:' + str(proposals))

def check_for_duplicate_samples(sampleNames):
    #sampleName must be unique
    sampleNamesSet = set()
    for sampleName in sampleNames:
        if sampleName in sampleNamesSet:
            raise Exception("duplicate sampleName: sampleName: %s" % (sampleName))
        sampleNamesSet.add(sampleName)

if __name__ == '__main__':
	info = []
	info.append('abcdef')
	check_sampleNames(info)
	info.append('abcdefghijklmnopqrstuvwxy1234')
	try:
		check_sampleNames(info)
	except:
		pass #expected failure
	check_for_sequence('filename.seq')
	try:
		check_for_sequence('ACDEFGHIIH')
	except:
		pass
	proposalNums = ['123456', 'su123456']
	try:
		check_proposalNum(proposalNums, '1234567')
	except:
		pass #expected failure with second item
