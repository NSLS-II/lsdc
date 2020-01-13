from __future__ import (absolute_import, print_function)

import sys
import os
import re

import mongoengine.connection

from ..db_lib import (db_connect, db_disconnect)
from .createTestDB import createTestDB

mongo_conn = None
db_name = None
db_host = None

# routines for database fixtures for testing

def dbtest_setup(collections):
    """
    """
    global mongo_conn, db_name, db_host

    db_disconnect(collections)
    print('connecting', file=sys.stderr)
    (mongo_conn, db_name, db_host) = db_connect()

    createTestDB()
        

def dbtest_teardown(collections, drop_db=True):
    """
    """

    if os.getenv('DB_LIB_KEEP_TEST_DB'):
        drop_db = False
    
    if drop_db != False:
        print('dropping', file=sys.stderr)
        mongo_conn.drop_database(db_name)

    print('disconnecting', file=sys.stderr)
    db_disconnect(collections)

    
def drop_all_tmp_dbs(mongo_conn, suffixroot=None):
    """
    Get all db's matching tmp suffix and drop them.
    """

    if suffixroot is None:
        suffixroot = os.getenv('DB_LIB_SUFFIXROOT')

    if suffixroot:
        re_obj = re.compile('^.*{0}[0-9a-f-]*$'.format(suffixroot))
        dbs_2drop = filter(re_obj.match, mongo_conn.database_names())
        map(print, dbs_2drop)
        map(mongo_conn.drop_database, dbs_2drop)

    else:
        print('no suffixroot arg passed and no DB_LIB_SUFFIX env var set', file=sys.stderr)


def copydb(fromdb, todb):
    client = mongoengine.connection.MongoClient()  # uses existing mongoengine connection?
    client.admin.command('copydb', fromdb=fromdb, todb=todb)
