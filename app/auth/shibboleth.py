# -*- coding: utf-8 -*-

from functools import wraps
from flask import abort, request, Response


def check_auth(headers):
    try:
        headers['eppn']
        return True
    except KeyError:
        return False


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not check_auth(request.headers):
            abort(403)
        return f(*args, **kwargs)

    return decorated
