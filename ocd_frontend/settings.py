import os.path

from dotenv import load_dotenv

from .helpers import root_path

DEBUG = True

# load .env file
load_dotenv(root_path('../.env'))

# Sendgrid settings
SENDGRID_API_KEY = os.environ.get('WO_SENDGRID_KEY')
SENDGRID_FROM_ADDRESS = 'no-reply@waaroverheid.nl'

# Celery settings
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/1')
CELERY_ACCEPT_CONTENT = ['pickle', 'json']

# Elasticsearch
ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'elasticsearch')
ELASTICSEARCH_PORT = os.getenv('ELASTICSEARCH_PORT', 9200)

# The default number of hits to return for a search request via the REST API
DEFAULT_SEARCH_SIZE = os.getenv('DEFAULT_SEARCH_SIZE', 10)

# The max. number of hits to return for a search request via the REST API
MAX_SEARCH_SIZE = os.getenv('MAX_SEARCH_SIZE', 100)

# The name of the index containing documents from all sources
COMBINED_INDEX = os.getenv('COMBINED_INDEX', 'ori_combined_index')

# the index storing subscriptions
SUBSCRIPTION_INDEX = os.getenv('SUBSCRIPTION_INDEX', 'alerts_wo')

# The default prefix used for all data
DEFAULT_INDEX_PREFIX = os.getenv('DEFAULT_INDEX_PREFIX', 'wo')

# The fields which can be used for sorting results via the REST API
SORTABLE_FIELDS = {
    'persons': [
        'meta.source_id', 'meta.processing_started', 'meta.processing_finished',
        'start_date', '_score', 'gender', 'name'],
    'organizations': [
        'meta.source_id', 'meta.processing_started', 'meta.processing_finished',
        'start_date', '_score', 'classification', 'name'],
    'events' : [
        'meta.source_id', 'meta.processing_started', 'meta.processing_finished',
        'start_date', '_score', 'classification', 'name', 'start_date',
        'location'],
    'motions': [
        'meta.source_id', 'meta.processing_started', 'meta.processing_finished',
        'start_date', '_score', 'classification', 'name', 'date'],
    'vote_events': [
        'meta.source_id', 'meta.processing_started', 'meta.processing_finished',
        'start_date', '_score', 'classification', 'name', 'start_date'],
    'items': [
        'meta.source_id', 'meta.processing_started', 'meta.processing_finished',
        'start_date', '_score']
}

EXCLUDED_FIELDS_ALWAYS = [
    'combined_index_data',
    'enrichments',
    'hidden',
]
EXCLUDED_FIELDS_DEFAULT = [
    'all_text',
    'source_data',
    'media_urls.original_url',
]
EXCLUDED_FIELDS_SEARCH = [
    'all_text',
    'media_urls.original_url'
]

ALLOWED_INCLUDE_FIELDS_DEFAULT = []
ALLOWED_INCLUDE_FIELDS_SEARCH = []

SIMPLE_QUERY_FIELDS = {
    'persons': ['name^3'],
    'organizations': ['name^4', 'description'],
    'events': [
        'name^4', 'description^3', 'location', 'organization.name',
        'organization.description', 'sources.note^2', 'sources.description'
    ],
    'motions': [
        'name^4', 'text^3', 'organization.name', 'sources.note^2',
        'sources.description'
    ],
    'vote_events': [
        'name^4', 'motion.text^3', 'organization.name', 'sources.note^2',
        'sources.description'
    ],
    'items': [
        'name^4', 'description^3', 'location', 'organization.name',
        'organization.description', 'sources.note^2', 'sources.description',
    ]
}

DOC_TYPE_DEFAULT = u'items'

# Definition of the ES facets (and filters) that are accessible through
# the REST API
COMMON_FACETS = {
    'processing_started': {
        'date_histogram': {
            'field': 'meta.processing_started',
            'interval': 'month'
        }
    },
    'processing_finished': {
        'date_histogram': {
            'field': 'meta.processing_finished',
            'interval': 'month'
        }
    },
    'source': {
        'terms': {
            'field': 'meta.source_id',
            'size': 10
        }
    },
    'collection': {
        'terms': {
            'field': 'meta.collection',
            'size': 10
        }
    },
    'rights': {
        'terms': {
            'field': 'meta.rights',
            'size': 10
        }
    },
    'index': {
        'terms': {
            'field': '_index',
            'size': 10
        }
    },
    'types': {
        'terms': {
            'field': '_type',
            'size': 10
        }
    },
    'start_date': {
        'date_histogram': {
            'field': 'start_date',
            'interval': 'month'
        }
     }
}

AVAILABLE_FACETS = {
    'organizations': {
        'classification': {
            'terms': {
                'field': 'classification',
                'size': 10
            }
        }
    },
    'persons': {
        'gender': {
            'terms': {
                'field': 'gender',
                'size': 2
            }
        },
        'organization': {
            'terms': {
                'field': 'memberships.organization_id',
                'size': 10
            }
        }
    },
    'events': {
        'classification': {
            'terms': {
                'field': 'classification',
                'size': 10
            }
        },
        'organization_id': {
            'terms': {
                'field': 'organization_id',
                'size': 10
            }
        },
        'location': {
            'terms': {
                'field': 'location',
                'size': 10
            }
        },
        'status': {
            'terms': {
                'field': 'status',
                'size': 10
            }
        },
        'start_date': {
            'date_histogram': {
                'field': 'start_date',
                'interval': 'month'
            }
        },
        'end_date': {
            'date_histogram': {
                'field': 'end_date',
                'interval': 'month'
            }
        },
    },
    'motions': {
        'classification': {
            'terms': {
                'field': 'classification',
                'size': 10
            }
        },
        'organization_id': {
            'terms': {
                'field': 'organization_id',
                'size': 10
            }
        },
        'legislative_session_id': {
            'terms': {
                'field': 'legislative_session_id',
                'size': 10
            }
        },
        'creator_id': {
            'terms': {
                'field': 'creator_id',
                'size': 10
            }
        },
        'date': {
            'date_histogram': {
                'field': 'date',
                'interval': 'month'
            }
        },
        'requirement': {
            'terms': {
                'field': 'requirement',
                'size': 10
            }
        },
        'result': {
            'terms': {
                'field': 'result',
                'size': 10
            }
        }
    },
    'vote_events': {
        'classification': {
            'terms': {
                'field': 'classification',
                'size': 10
            }
        },
        'organization_id': {
            'terms': {
                'field': 'organization_id',
                'size': 10
            }
        },
        'start_date': {
            'date_histogram': {
                'field': 'start_date',
                'interval': 'month'
            }
        },
        'end_date': {
            'date_histogram': {
                'field': 'end_date',
                'interval': 'month'
            }
        },
        'legislative_session_id': {
            'terms': {
                'field': 'legislative_session_id',
                'size': 10
            }
        }
    },
    'items': {
        'classification': {
            'terms': {
                'field': 'classification',
                'size': 10
            }
        },
        'neighborhoods': {
            'terms': {
                'field': 'neighborhoods',
                'size': 10,
            }
        },
        'districts': {
            'terms': {
                'field': 'districts',
                'size': 10,
            }
        }
    }
}

# For highlighting
COMMON_HIGHLIGHTS = {
    'source': {},
    'collection': {},
    'rights': {}
}

AVAILABLE_HIGHLIGHTS = {
    'organizations': {
        'classification': {},
        'name': {},
        'description': {}
    },
    'persons': {
        'name': {},
        'memberships.role': {},
        'area.name': {}
    },
    'events': {
        'classification': {},
        'location': {},
        'organization.name': {},
        'description': {},
        'sources.note': {},
        'sources.description': {}
    },
    'motions': {
        'classification': {},
        'organization.name': {},
        'creator.name': {},
        'text': {},
        'sources.description': {}
    },
    'vote_events': {
        'classification': {},
        'organization.name': {},
        'creator.name': {},
        'text': {},
        'sources.description': {}
    },
    'items': {
        'classification': {},
        'name': {},
        'description': {}
    }
}

# The allowed date intervals for an ES data_histogram that can be
# requested via the REST API
ALLOWED_DATE_INTERVALS = ('day', 'week', 'month', 'quarter', 'year')

# Name of the Elasticsearch index used to store URL resolve documnts
RESOLVER_URL_INDEX = os.getenv('RESOLVER_URL_INDEX', 'ori_resolver')

# Determines if API usage events should be logged
USAGE_LOGGING_ENABLED = True
# Name of the Elasticsearch index used to store logged events
USAGE_LOGGING_INDEX = os.getenv('USAGE_LOGGING_INDEX', 'usage_logs_wo')
# Name of the Elasticsearch index used for user feedback
USER_FEEDBACK_INDEX = os.getenv('USER_FEEDBACK_INDEX', 'user_feedback_wo')

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
DUMPS_DIR = os.path.join(os.path.dirname(ROOT_PATH), 'dumps')
LOCAL_DUMPS_DIR = os.path.join(os.path.dirname(ROOT_PATH), 'local_dumps')
DATA_DIR_PATH = os.path.dirname(ROOT_PATH)

# URL where of the API instance that should be used for management commands
# Should include API version and a trailing slash.
# Can be overridden in the CLI when required, for instance when the user wants
# to download dumps from another API instance than the one hosted by OpenState
API_URL = os.getenv('API_URL', 'http://frontend:5000/v0/')

# URL where collection dumps are hosted. This is used for generating full URLs
# to dumps in the /dumps endpoint
DUMP_URL = os.getenv('DUMP_URL', 'http://dumps.opencultuurdata.nl/')

LOGGING = {
    'version': 1,
    'formatters': {
        'console': {
            'format': '[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'console'
        },
    },
    'loggers': {
        'ocd_frontend': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        }
    }
}

THUMBNAILS_TEMP_DIR = '/tmp'

THUMBNAILS_MEDIA_TYPES = {'image/jpeg', 'image/png', 'image/tiff'}
THUMBNAILS_DIR = os.path.join(ROOT_PATH, '.thumbnail-cache')

THUMBNAIL_SMALL = 250
THUMBNAIL_MEDIUM = 500
THUMBNAIL_LARGE = 1000

THUMBNAIL_SIZES = {
    'large': {'size': (THUMBNAIL_LARGE, THUMBNAIL_LARGE), 'type': 'aspect'},
    'medium': {'size': (THUMBNAIL_MEDIUM, THUMBNAIL_MEDIUM), 'type': 'aspect'},
    'small': {'size': (THUMBNAIL_SMALL, THUMBNAIL_SMALL), 'type': 'aspect'},
    'large_sq': {'size': (THUMBNAIL_LARGE, THUMBNAIL_LARGE), 'type': 'crop'},
    'medium_sq': {'size': (THUMBNAIL_MEDIUM, THUMBNAIL_MEDIUM), 'type': 'crop'},
    'small_sq': {'size': (THUMBNAIL_SMALL, THUMBNAIL_SMALL), 'type': 'crop'},
}

THUMBNAIL_URL = '/media/'


# Allow any settings to be defined in local_settings.py which should be
# ignored in your version control system allowing for settings to be
# defined per machine.
try:
    from local_settings import *
except ImportError:
    pass
