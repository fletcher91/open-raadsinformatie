from collections import defaultdict

from elasticsearch import Elasticsearch
from flask import render_template

from ocd_frontend import mail
from ocd_frontend import settings


class ElasticsearchService(object):
    def __init__(self, host, port):
        self._es = Elasticsearch([{'host': host, 'port': port}])

    def search(self, *args, **kwargs):
        return self._es.search(*args, **kwargs)

    def create(self, *args, **kwargs):
        return self._es.create(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._es.get(*args, **kwargs)

    def exists(self, *args, **kwargs):
        return self._es.exists(*args, **kwargs)

    def msearch(self, *args, **kwargs):
        return self._es.msearch(*args, **kwargs)

    def index(self, *args, **kwargs):
        return self._es.index(*args, **kwargs)

    def update(self, *args, **kwargs):
        return self._es.update(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._es.delete(*args, **kwargs)

    def put_template(self, *args, **kwargs):
        return self._es.indices.put_template(*args, **kwargs)


def get_percolate_query(document):
    return {
        "query": {
            "constant_score": {
                "filter": {
                    "percolate": {
                        "field": "query",
                        "document_type": document["_index"],
                        "id": document["_id"],
                        "type": document["_type"],
                        "index": document["_index"],
                    }
                }
            }
        }
    }


def percolate_documents(documents, latest_date, dry_run=False):
    es = ElasticsearchService(
        settings.ELASTICSEARCH_HOST, settings.ELASTICSEARCH_PORT)

    print('running percolate over {} documents'.format(len(documents)))

    subscriptions = {}
    matched_documents = defaultdict(list)

    for document in documents:
        query = get_percolate_query(document)
        result = es.search(index=settings.SUBSCRIPTION_INDEX, doc_type=document['_index'], body=query)
        for hit in result['hits']['hits']:
            subscription = hit['_source']
            if subscription['activated']:
                subscriptions[hit['_id']] = subscription
                matched_documents[hit['_id']].append(document)

    for subscription_id, subscription in subscriptions.items():
        docs = matched_documents[subscription_id]
        doc_count = len(docs)
        print("subscription {}: found {} docs, sending email to {}"
              .format(subscription_id, doc_count, subscription['email']))

        if not dry_run:
            email_subscription(subscription, doc_count, latest_date)


def email_subscription(subscription, doc_count, latest_date):
        new_since = latest_date
        if hasattr(new_since, 'isoformat'):
            new_since = new_since.isoformat()

        email_body = render_template(
            'alert_email.txt',
            subscription=subscription,
            token=subscription['token'],
            doc_count=doc_count,
            latest_date=new_since,
        )
        mail.send(
            subscription['email'],
            'Nieuwe resultaten beschikbaar voor uw opgeslagen zoekopdracht in {}'
            .format(subscription.get('area_name', subscription['querystring'])),
            email_body,
        )
