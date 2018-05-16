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


def percolate_documents(documents, latest_date):
    print('running percolate over {} documents'.format(len(documents)))

    es = ElasticsearchService(
        settings.ELASTICSEARCH_HOST, settings.ELASTICSEARCH_PORT)
    result = es.search(index=settings.SUBSCRIPTION_INDEX, body={
        "query": {
            "constant_score": {
                "filter": {
                    "percolate": {
                        "field": "query",
                        "documents": documents,
                    }
                }
            }
        }
    })

    for hit in result['hits']['hits']:
        print('got hit: ', hit['_source']['token'])
        subscription = hit['_source']
        document_indexes = hit['fields']['_percolator_document_slot']

        matched_documents = [documents[x] for x in document_indexes]

        mail.send(
            subscription['email'],
            'New documents match your stored search',
            render_template(
                'subscription_documents.txt',
                subscription=subscription,
                token=subscription['token'],
                docs=matched_documents,
                latest_date=latest_date,
            )
        )
