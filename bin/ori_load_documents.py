#! /usr/bin/env python2

from __future__ import print_function, unicode_literals

import argparse
import json
import re
from datetime import datetime

import requests
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan, bulk
from tqdm import tqdm


parser = argparse.ArgumentParser()
parser.add_argument('source_collection', help='The ES index used as data source')
parser.add_argument('municipality_code', help='CBS municipality code "GM\d\d\d\d"')
args = parser.parse_args()


ES_HOST = 'localhost'
ES_SOURCE_PORT = 9797
ES_SINK_PORT = 9200

es_source = Elasticsearch([{'host': ES_HOST, 'port': ES_SOURCE_PORT}])
es_sink = Elasticsearch([{'host': ES_HOST, 'port': ES_SINK_PORT}])

# input validation
if not es_source.indices.exists(index=args.source_collection):
    print('Source collection {} cannot be found'.format(args.source_collection))

mun_code_re_str = r'GM\d{4}$'
if not re.match(mun_code_re_str, args.municipality_code):
    print('Municipality code must match the regex r"{}"'.format(mun_code_re_str))


def geocode_collection(source_index, municipality_code):
    waaroverheid_index = 'wo_{}'.format(municipality_code.lower())
    print('Geocoding {} into {}'.format(source_index, waaroverheid_index))
    total_count = es_source.count(index=source_index)['count']

    chunk_size = 25
    items = scan(
        es_source,
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
                bulk(es_sink, new_items, chunk_size=chunk_size, request_timeout=120)
                progress_bar.update(chunk_size)
                new_items = []

        bulk(es_sink, new_items, chunk_size=chunk_size, request_timeout=120)
        progress_bar.update(len(new_items))


def get_fields_to_annotate(doc, doc_type):
    body = doc['_source']
    if doc_type == 'events':
        return [body] + body.get('sources', [])
    elif doc_type == 'vote_events':
        motion = body.get('motion')
        if motion:
            return [motion] + body.get('sources', [])
        else:
            return body.get('sources', [])
    else:
        return None


def annotate_document(doc, municipality_code):
    # they're sets because we want to keep duplicates away
    municipal_refs = {
        'districts': set(),
        'neighborhoods': set(),
    }

    text_fields = get_fields_to_annotate(doc, doc['_type'])
    if not text_fields:
        return doc

    errors = []
    for source in text_fields:
        field_key = 'description'
        text = source.get(field_key, '')

        if not text:
            field_key = 'text'
            text = source.get(field_key, '')

        clean_text = text.replace('-\n', '')
        if clean_text:
            source[field_key] = clean_text
        else:
            continue

        resp = requests.post('https://api.waaroverheid.nl/annotate', json={
            'municipality_code': municipality_code,
            'text': clean_text
        })

        if not resp.ok:
            print('ERROR annotating: ', resp.status_code, resp.text)
            error_dict = {
                'doc_id': doc['_id'],
                'doc_type': doc['_type'],
                'doc_index': doc['_index'],
                'municipality_code': municipality_code,
                'status_code': resp.status_code,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            if resp.status_code == 500:
                error_dict['text'] = clean_text
            errors.append(error_dict)
            continue

        data = resp.json()
        source['annotations'] = data['annotations']
        municipal_refs['districts'].update(data['districts'])
        municipal_refs['neighborhoods'].update(data['neighborhoods'])

    # convert to lists to make sure we can serialize to JSON
    doc['_source']['districts'] = sorted(municipal_refs['districts'])
    doc['_source']['neighborhoods'] = sorted(municipal_refs['neighborhoods'])

    if errors:
        # write errors to json lines
        with open('log/geocoding_errors_{}.log'.format(municipality_code), 'a') as f:
            for error_dict in errors:
                f.write(json.dumps(error_dict) + '\n')

    return doc


if __name__ == '__main__':
    geocode_collection(args.source_collection, args.municipality_code)
