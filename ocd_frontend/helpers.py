import json
import pkgutil
import importlib

from flask import Blueprint
from os import path


FRONTEND_ROOT = path.dirname(
    path.abspath(__file__)
)


def root_path(*args):
    return path.join(FRONTEND_ROOT, *args)


def register_blueprints(app, package_name, package_path):
    """Register all Blueprint instances on the specified Flask
    application found in all modules for the specified package.

    :param app: Flask application.
    :param package_name: package name.
    :param package_path: package path.
    """
    rv = []

    for _, name, _ in pkgutil.iter_modules(package_path):
        m = importlib.import_module('%s.%s' % (package_name, name))
        for item in dir(m):
            item = getattr(m, item)
            if isinstance(item, Blueprint):
                app.register_blueprint(item)
            rv.append(item)

    return rv


def nltk_data(file_name):
    return path.join(
        path.abspath(path.dirname(__file__)),
        'nltk-data',
        file_name
    )


def put_mapping_template(es_service, template_name):
    template_file = template_name + '.json'
    with open(root_path('es_mappings', template_file)) as f:
        log_template = json.load(f)

    print('Putting {} as template for {}'.format(template_file, log_template['template']))
    es_service.put_template(template_name, log_template)
