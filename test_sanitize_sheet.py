import sanitize_sheet
import pytest

def test_check_info():
    info = ['abcdef']
    assert(sanitize_sheet.check_sampleNames(info))
    info = ['abcdefghijklmnopqrstuvwxy1234']
    with pytest.raises(Exception):
        sanitize_sheet.check_info(info)
def test_check_for_sequence():
    assert(sanitize_sheet.check_for_sequence([float('nan')]))
    assert(sanitize_sheet.check_for_sequence(['filename.seq']))
    with pytest.raises(Exception):
        sanitize_sheet.check_for_sequence(['ACDEFGHIIH'])
def test_proposalNum():
    proposalNums = ['123456']
    assert(sanitize_sheet.check_proposalNum(proposalNums))
    proposalNums = ['su123456']
    with pytest.raises(Exception):
        sanitize_sheet.check_proposalNum(proposalNums)
