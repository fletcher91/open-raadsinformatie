#! /usr/bin/env python2

from __future__ import print_function, unicode_literals

import requests
from elasticsearch import Elasticsearch


GM_CODE = 'GM0344'
ORI_API_URL = "http://api.openraadsinformatie.nl/v0"
ES_HOST = 'localhost'
ES_PORT = 9200

es = Elasticsearch([{'host': ES_HOST, 'port': ES_PORT}])


def iter_documents(source, type_, cursor=0):
    url = "{url}/{source}/{type}/search".format(
        url=ORI_API_URL, source=source, type=type_)

    while True:
        resp = requests.post(url, json={
            'size': 20,
            'from': cursor,
        })

        if not resp.ok:
            print("ERROR fetching docs: ", resp.status_code, resp.text)
            if raw_input('continue (y/n)? ').lower() == 'y':
                cursor += 20
                continue
            return

        results = resp.json()['events']
        for doc in results:
            yield doc

        # see if we need to stop or fetch more docs
        if len(results) < 20:
            break
        else:
            cursor += 20


def get_fields_to_annotate(doc, doc_type):
    if doc_type == 'event':
        return doc.get('sources', [])


def annotate_document(doc, gm_code):
    # they're sets because we want to keep duplicates away
    annotations = {
        'districts': set(),
        'annotations': [],
        'neighborhoods': set(),
    }

    for source in get_fields_to_annotate(doc, 'event'):
        resp = requests.post('https://api.waaroverheid.nl/annotate', json={
            'municipality_code': gm_code,
            'text': source['description']
        })

        if not resp.ok:
            print("ERROR annotating: ", resp.status_code, resp.text)
            print(resp.request.body)
            continue

        data = resp.json()
        annotations['districts'].update(data['districts'])
        annotations['annotations'].extend(data['annotations'])
        annotations['neighborhoods'].update(data['neighborhoods'])

    # convert to lists to make sure we can serialize to JSON
    doc['districts'] = list(annotations['districts'])
    doc['neighborhoods'] = list(annotations['neighborhoods'])
    doc['annotations'] = annotations['annotations']
    return doc


def store_documents(index_name, documents):
    for idx, document in enumerate(documents):
        print('{}: Annotating document {}: {}'.format(
            idx, document['meta']['_type'], document['name']))
        document = annotate_document(document, GM_CODE)
        document['hidden'] = False
        es.index(
            index=index_name,
            id=document['id'],
            doc_type=document['meta']['_type'],
            body=document
        )


if __name__ == "__main__":
    docs = iter_documents('utrecht', 'events')
    store_documents('ori_combined_index', docs)
