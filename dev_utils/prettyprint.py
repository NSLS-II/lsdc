# from https://gist.github.com/mrcoles/4074837

from __future__ import print_function

from bson import json_util, ObjectId
from bson.py3compat import string_types
from bson.dbref import DBRef

from IPython.core import page


DEFAULT_INDENT = 4


def _dbref_fix(obj):
    """
    Recursive helper method that converts BSON ObjectId types so they can be
    converted by bson.json_util.dumps into json.
    Created to deal with a situation like this:
    "collection" : { "$ref" : "collection", "$id" : { "$oid" : "505cdd127e89297d6f000421" } }
    """
    if hasattr(obj, 'iteritems') or hasattr(obj, 'items'):  # PY3 support
        #return {k: _dbref_fix(v) for k, v in obj.iteritems()}
        ret = {}
        for k,v in obj.iteritems():
            ret[k] = v
        return ret

    elif hasattr(obj, '__iter__') and not isinstance(obj, string_types):
        return [_dbref_fix(v) for v in obj]

    elif isinstance(obj, DBRef):
        id = obj.id
        coll = obj.collection
        db = obj.database
        d = {}
        if id: d['$id'] = {'$oid': str(id)}
        if coll: d['$ref'] = coll
        if db: d['$db'] = db
        return d

    else:
        return obj


def format_(bson, indent=DEFAULT_INDENT):
    """
    Takes a bson document, returns a pretty printed string.
    DEFAULT_INDENT={0}
    """

    d = _dbref_fix(bson)
    return json_util.dumps(d, indent=indent)

def print_(bson, indent=DEFAULT_INDENT):
    """
    Takes a bson document and pretty prints it.
    DEFAULT_INDENT={0}
    """
    print(format_(bson, indent=indent))

def ppp(bson, indent=DEFAULT_INDENT):
    """
    Takes a bson document, pretty prints, and pages it. (for ipython shell)
    DEFAULT_INDENT={0}
    """
    page.page(format_(bson, indent=indent))
