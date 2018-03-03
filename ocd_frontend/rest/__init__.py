from functools import wraps
import json

import sys
from flask import jsonify, request

from ocd_frontend.factory import create_app_factory
from ocd_frontend.helpers import root_path, put_mapping_template


def create_app(settings_override=None):
    """Returns the REST API application instance."""
    app = create_app_factory(__name__, __path__, settings_override)
    app.errorhandler(OcdApiError)(OcdApiError.serialize_error)

    def add_cors_headers(resp):
        resp.headers['Access-Control-Allow-Origin'] = '*'
        # See https://stackoverflow.com/questions/12630231/how-do-cors-and-access-control-allow-headers-work
        resp.headers['Access-Control-Allow-Headers'] = 'origin, content-type, accept'
        return resp

    app.after_request(add_cors_headers)

    put_alerts_template(app.es)
    put_mapping_template(app.es, 'ori_usage_logs')
    put_mapping_template(app.es, 'wo_user_feedback')
    sys.stdout.flush()

    return app


def put_alerts_template(es_service):
    template_file = 'wo_alerts.json'
    with open(root_path('es_mappings', template_file)) as f:
        template = json.load(f)

    with open(root_path('es_mappings', 'wo_template.json')) as f:
        mapping_template = json.load(f)

    template['settings']['index']['analysis'] = mapping_template['settings']['index']['analysis']
    template['mappings']['document'] = {
        'properties': mapping_template['mappings']['_default_']['properties']
    }

    print('Putting {} as template for {}'.format(
        template_file, template['template']))
    es_service.put_template(template_file[:-5], template)


class OcdApiError(Exception):
    """API error class.

    :param msg: the message that should be returned to the API user.
    :param status_code: the HTTP status code of the response
    """

    def __init__(self, msg, status_code):
        self.msg = msg
        self.status_code = status_code

    def __str__(self):
        return repr(self.msg)

    @staticmethod
    def serialize_error(e):
        return jsonify(dict(status='error', error=e.msg)), e.status_code


def decode_json_post_data(fn):
    """Decorator that parses POSTed JSON and attaches it to the request
    object (:obj:`request.data`)."""

    @wraps(fn)
    def wrapped_function(*args, **kwargs):
        if request.method == 'POST':
            data = request.get_data(cache=False)
            if not data:
                raise OcdApiError('No data was POSTed', 400)

            try:
                request_charset = request.mimetype_params.get('charset')
                if request_charset is not None:
                    data = json.loads(data, encoding=request_charset)
                else:
                    data = json.loads(data)
            except:
                raise OcdApiError('Unable to parse POSTed JSON', 400)

            request.data = data

        return fn(*args, **kwargs)

    return wrapped_function
