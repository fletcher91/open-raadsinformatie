#! /usr/bin/env python2

from __future__ import print_function, unicode_literals

import argparse
import json
import os
import re
import requests
import sys
from datetime import datetime

from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import scan, bulk
from pygtrie import CharTrie
from pymongo import MongoClient
from tqdm import tqdm

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)
sys.path.insert(0, os.path.abspath(BASE_DIR))

from ocd_frontend.rest.snippets import add_doc_snippets
from ocd_frontend.rest import tasks
from ocd_frontend.es import percolate_documents


parser = argparse.ArgumentParser()
parser.add_argument(
    'source_collection',
    default=None,
    nargs='?',
    help='The ES index used as data source'
)
parser.add_argument(
    'municipality_code',
    default=None,
    nargs='?',
    help='CBS municipality code "GM\d\d\d\d"'
)
args = parser.parse_args()


ES_HOST = 'localhost'
ES_SOURCE_PORT = 9797
ES_SINK_PORT = 9200

es_source = Elasticsearch([{'host': ES_HOST, 'port': ES_SOURCE_PORT}], timeout=30)
es_sink = Elasticsearch([{'host': ES_HOST, 'port': ES_SINK_PORT}])

mongo_client = MongoClient()
llv_db = mongo_client.osm_globe


def geocode_collection(source_index, municipality_code):
    print('\nGeocoding {} for municipality {}'.format(source_index, municipality_code))
    waaroverheid_index = 'wo_{}'.format(municipality_code.lower())
    source_count = es_source.count(index=source_index)['count']
    try:
        sink_count = es_sink.count(index=waaroverheid_index)['count']
    except NotFoundError:
        sink_count = 0

    if source_count > sink_count:
        latest_date, buckets = get_incomplete_buckets(source_index, waaroverheid_index)
        docs = []
        for bucket in buckets:
            bucket_docs = load_bucket(source_index, municipality_code, latest_date, bucket)
            docs.extend(bucket_docs)
            tasks.email_subscribers.apply(args=[bucket_docs, latest_date])

        sink_count = es_sink.count(index=waaroverheid_index)['count']
    else:
        print('Skipping: source {} docs, sink {} docs'.format(source_count, sink_count))

    # update doc counts in MongoDB
    for db_collection in ['municipality_highover', 'municipality_closeup']:
        llv_db[db_collection].update_one(
            {'properties.GM_CODE': municipality_code},
            {'$set': {
                'properties.doc_count': sink_count
            }}
        )


def load_bucket(source_index, municipality_code, latest_date, bucket):
    waaroverheid_index = 'wo_{}'.format(municipality_code.lower())

    date_from = bucket['key_as_string']
    if latest_date and latest_date['value'] > bucket['key']:
        date_from = latest_date['value_as_string']

    date_till = bucket['key_as_string'] + '||+1w'
    print('{} from {} till {}'.format(source_index, date_from, date_till))

    es_query = {
        'query': {
            'bool': {
                'must': {'match_all': {}},
                'filter': {
                    'range': {
                        'meta.processing_started': {
                            'gt': date_from,
                            'lte': date_till
                        }
                    }
                }
            }
        },
        'sort': [
            {'meta.processing_started': {'order': 'asc'}},
        ]
    }

    chunk_size = 25
    items = scan(
        es_source,
        query=es_query,
        index=source_index,
        scroll='10m',
        size=chunk_size,
        preserve_order=True,
        raise_on_error=False,
    )

    new_items = []
    indexed_docs = []
    with tqdm(total=bucket['doc_count']) as progress_bar:
        for item in items:
            item['_index'] = waaroverheid_index
            del item['_score']
            # TODO: exclude fields in query
            item['_source'].pop('source_data')
            item['_source'].pop('combined_index_data')
            if 'meta' in item['_source']:
                item['_source']['meta'] = {
                    k: v
                    for k, v in item['_source']['meta'].items()
                    if not k.startswith('_')
                }

            annotated_item = annotate_document(item, municipality_code)
            add_doc_snippets(annotated_item['_source'])

            new_items.append(annotated_item)
            indexed_docs.append(annotated_item)
            if len(new_items) >= chunk_size:
                bulk(es_sink, new_items, chunk_size=chunk_size,
                     request_timeout=120)
                progress_bar.update(chunk_size)
                new_items = []

        bulk(es_sink, new_items, chunk_size=chunk_size, request_timeout=120)
        progress_bar.update(len(new_items))
    return indexed_docs


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
        with open(os.path.join(
            BASE_DIR,
            'log/geocoding_errors_{}.log'.format(municipality_code)
        ), 'a') as f:
            for error_dict in errors:
                f.write(json.dumps(error_dict) + '\n')

    return doc


def get_available_collections():
    aliases_by_index = es_source.indices.get_alias(name='ori_*')
    aliases_by_collection = CharTrie({
        alias[4:]: alias
        for props in aliases_by_index.values()
        for alias in props['aliases']
    })

    def get_alias(collection):
        if aliases_by_collection.has_subtrie(collection + '_'):
            return u'ori_{}_*'.format(collection)
        else:
            return aliases_by_collection.get(collection)

    ori_base_url = 'http://api.openraadsinformatie.nl/v0/'
    resp = requests.post(ori_base_url + 'search/organizations', json={
        'filters': {
            'classification': {
                'terms': ['Municipality']
            }
        },
        'size': 500
    })
    data = resp.json()
    if data['meta']['total'] > 500:
        print('WARNING: only loading 500/{} municipalities'.format(data['meta']['total']))

    available_collections = {
        next(
            ref['identifier']
            for ref in org['identifiers']
            if ref['scheme'] == 'CBS'
        ): {
            'ori_name': org['name'],
            'ori_alias': get_alias(org['meta']['collection'])
        }
        for org in data['organizations']
    }
    return available_collections


def get_date_aggregations(es_connection, alias, date_from=None):
    if not es_connection.indices.exists(index=alias):
        return None, None

    es_query = {
        'aggs': {
            'by_processing_date': {
                'date_histogram': {
                    'field': 'meta.processing_started',
                    'interval': 'week'
                }
            },
            'latest_date': {
                'max': {
                    'field': 'meta.processing_started',
                }
            },
        },
        'query': {
            'bool': {
                'must': {'match_all': {}},
                'filter': {}
            }
        },
        'size': 0
    }
    if date_from:
        es_query['query']['bool']['filter'] = {
            'range': {
                'meta.processing_started': {
                    'gt': date_from
                }
            }
        }
    resp = es_connection.search(index=alias, body=es_query)

    return (
        resp['aggregations']['latest_date'],
        resp['aggregations']['by_processing_date']['buckets']
    )


def get_incomplete_buckets(ori_alias, waaroverheid_index):
    latest_sink_date, sink_buckets = get_date_aggregations(es_sink, waaroverheid_index)
    if not latest_sink_date:
        return None, get_date_aggregations(es_source, ori_alias)[1]

    _, source_buckets = get_date_aggregations(
        es_source, ori_alias, date_from=latest_sink_date['value_as_string']
    )
    sink_by_week = {
        week['key']: week
        for week in sink_buckets
    }
    incomplete_weeks = []
    for week in source_buckets:
        sink_count = 0
        try:
            sink_count = sink_by_week[week['key']]['doc_count']
        except KeyError:
            pass

        if week['doc_count'] > sink_count:
            incomplete_weeks.append(week)

    return latest_sink_date, incomplete_weeks


if __name__ == '__main__':
    # PUT Elasticsearch mapping template
    wo_template_file = 'wo_template.json'
    with open(os.path.join(BASE_DIR, 'es_mappings', wo_template_file)) as f:
        wo_template = json.load(f)

    print('Putting {} as template for {}'.format(wo_template_file, wo_template['template']))
    es_sink.indices.put_template('ori_template', wo_template)

    # input validation
    if args.source_collection and args.municipality_code:
        if not es_source.indices.exists(index=args.source_collection):
            print('Source collection {} cannot be found'.format(args.source_collection))

        mun_code_re_str = r'GM\d{4}$'
        if not re.match(mun_code_re_str, args.municipality_code):
            print('Municipality code must match the regex r"{}"'.format(mun_code_re_str))

        geocode_collection(args.source_collection, args.municipality_code)
    else:
        print('Loading all available collections...')
        ori_collections = get_available_collections()
        for i, code__props in enumerate(sorted(ori_collections.iteritems())):
            cbs_code, ori_props = code__props
            print('\n' * 5 + u'{}/{} -- {}'.format(1 + i, len(ori_collections), ori_props['ori_name']))
            geocode_collection(ori_props['ori_alias'], cbs_code)
