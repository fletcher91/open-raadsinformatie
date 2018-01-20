#! /usr/bin/env python2

from __future__ import print_function, unicode_literals

import argparse
import re

import requests
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan, bulk
from tqdm import tqdm


parser = argparse.ArgumentParser()
parser.add_argument("source_collection", help="The ES index used as data source")
parser.add_argument("municipality_code", help="CBS municipality code 'GM\d\d\d\d'")
args = parser.parse_args()


ES_HOST = 'localhost'
ES_PORT = 9200

es = Elasticsearch([{'host': ES_HOST, 'port': ES_PORT}])

# input validation
if not es.indices.exists(index=args.source_collection):
    print('Source collection {} cannot be found'.format(args.source_collection))

mun_code_re_str = r'GM\d{4}$'
if not re.match(mun_code_re_str, args.municipality_code):
    print('Municipality code must match the regex r"{}"'.format(mun_code_re_str))


def geocode_collection(source_index, municipality_code):
    waaroverheid_index = 'wo_{}'.format(municipality_code.lower())
    print('Geocoding {} into {}'.format(source_index, waaroverheid_index))
    total_count = es.count(index=source_index)['count']

    chunk_size = 25
    items = scan(
        es,
        query=None,
        index=source_index,
        scroll='10m',
        size=chunk_size,
        raise_on_error=False,
    )

    new_items = []
    with tqdm(total=total_count) as progress_bar:
        for item in items:
            item['_index'] = waaroverheid_index
            del item['_score']
            item['_source'].pop('source_data')
            item['_source'].pop('combined_index_data')
            if 'meta' in item['_source']:
                item['_source']['meta'] = {
                    k: v
                    for k, v in item['_source']['meta'].items()
                    if not k.startswith('_')
                }

            annotated_item = annotate_document(item, municipality_code)
            new_items.append(annotated_item)
            if len(new_items) >= chunk_size:
                bulk(es, new_items, chunk_size=chunk_size, request_timeout=120)
                progress_bar.update(chunk_size)
                new_items = []

        bulk(es, new_items, chunk_size=chunk_size, request_timeout=120)
        progress_bar.update(len(new_items))


def get_fields_to_annotate(doc, doc_type):
    # TODO: description,
    if doc_type == 'event':
        return doc.get('sources', [])
    else:
        return None


def annotate_document(doc, municipality_code):
    # they're sets because we want to keep duplicates away
    annotations = {
        'districts': set(),
        'annotations': [],
        'neighborhoods': set(),
    }

    text_fields = get_fields_to_annotate(doc, doc['_type'])
    if not text_fields:
        return doc

    for source in text_fields:
        clean_text = source['description'].replace('-\n', '')
        source['description'] = clean_text

        resp = requests.post('https://api.waaroverheid.nl/annotate', json={
            'municipality_code': municipality_code,
            'text': clean_text
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
    doc['districts'] = sorted(annotations['districts'])
    doc['neighborhoods'] = sorted(annotations['neighborhoods'])
    doc['annotations'] = annotations['annotations']
    return doc


if __name__ == "__main__":
    geocode_collection(args.source_collection, args.municipality_code)
