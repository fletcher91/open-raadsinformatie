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
    q = {'query': { 'match_all': {}}}
    result = scan(client=es, query=q, index=settings.SUBSCRIPTION_INDEX)
    return result


def find_matching_docs(subscription, loaded_since, es):
    query = {"query": subscription['_source']['query']}
    query['query']['bool']['filter'] = {
        'range': {
            'meta.processing_finished': {'gt': loaded_since}
        }
    }
    try:
        result = es.search(
            body=query,
            index=subscription["_type"],
        )
    except NotFoundError:
        return 0, []

    return result['hits']['total'], result['hits']['hits']


def main(args):
    es = get_elasticsearch_connection()

    for subscription in get_subscriptions(es):
        doc_count, doc_sample = find_matching_docs(
            subscription, args.loaded_since, es)

        if doc_count > 0:
            print("subscription {}: found {} docs, sending email"
                  .format(subscription['_id'], doc_count))
            if not args.dry_run:
                email_subscription(subscription, doc_sample, doc_count,
                                   latest_date)
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
