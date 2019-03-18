#! /usr/bin/env python2

from __future__ import print_function, unicode_literals

import argparse
import datetime
import os
import sys

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from elasticsearch.helpers import scan

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)
sys.path.insert(0, os.path.abspath(BASE_DIR))

from ocd_frontend import settings
from ocd_frontend.es import email_subscription
from ocd_frontend.rest import create_app


def parse_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        msg = 'Not a valid date: {}'.format(date_str)
        raise argparse.ArgumentTypeError(msg)


def get_elasticsearch_connection():
    ES_HOST, ES_PORT = 'localhost', 9200
    return Elasticsearch([{'host': ES_HOST, 'port': ES_PORT}])


def get_subscriptions(es):
    q = {'query': {'match_all': {}}}
    subscriptions = []
    subscription_hits = scan(client=es, query=q, index=settings.SUBSCRIPTION_INDEX)
    for hit in subscription_hits:
        hit.update(hit.pop('_source'))
        # FIXME: might as well query for activated subscriptions
        if hit['activated']:
            subscriptions.append(hit)

    return subscriptions


def find_matching_docs(subscription, loaded_since, es):
    query = {'query': subscription['query']}
    query['query']['bool']['filter'].append({
        'range': {
            'meta.processing_finished': {'from': loaded_since}
        }
    })
    query['query']['bool']['should'] = [
	{
	    'exists': {
		'field': 'sources.snippets'
	    }
	},
	{
	    'exists': {
		'field': 'description'
	    }
	},
    ]
    query['query']['bool']['minimum_should_match'] = 1
    try:
        result = es.search(
            body=query,
            index=subscription["_type"],
        )
    except NotFoundError:
        return 0, []

    # FIXME: hit count is not the same as with the URI and frontend
    return result['hits']['total'], result['hits']['hits']


def main(args):
    es = get_elasticsearch_connection()
    app = create_app({'ELASTICSEARCH_HOST': 'localhost'})

    for subscription in get_subscriptions(es):
        doc_count, doc_sample = find_matching_docs(
            subscription, args.loaded_since, es)

        if doc_count > 0:
            print("subscription {}: found {} docs, sending email to {}"
                  .format(subscription['_id'], doc_count, subscription['email']))
            if not args.dry_run:
                with app.app_context():
                    email_subscription(subscription, doc_count, args.loaded_since)
        else:
            print("subscription {}: no docs found, skipping"
                  .format(subscription['_id']))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'loaded_since',
        type=parse_date,
        help='send notification for documents after this date (format: YYYY-MM-DD'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="don't send emails, just pretend to do everything"
    )

    args = parser.parse_args()
    main(args)
