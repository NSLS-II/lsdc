import re
import magic
import tempfile
import subprocess

import lsdc


def display_file(ref_or_id):
    """
    Take a dbref or oid, fetch the item from the File collection,
    return it if it's text, display it if it's an image, or print an error.
    """
    file_data = lsdc.db_lib.getFile(ref_or_id)

    with magic.Magic(magic.MAGIC_NONE) as m:
        description = m.buffer(file_data)

    if re.search('image', description):
        image = True
        
    elif not re.search('text', description):
        print('\nunsupported file type: {0}\n'.format(description))
        # should dump and leave a tmpfile in this case
        return

    if image:
        # dump the image to a temporary file
        with tempfile.NamedTemporaryFile('w+') as tmp_fd:
            tmp_fd.write(file_data)
            tmp_fname = tmp_fd.name
            subprocess.call(['display', tmp_fname])

    else:
        #print '----------------------------------------------------------------------'
        #print file_data
        return file_data
        #print '----------------------------------------------------------------------'
