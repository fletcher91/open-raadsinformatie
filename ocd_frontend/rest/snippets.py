from collections import defaultdict

import nltk
from intervaltree import IntervalTree, Interval

from ocd_frontend.helpers import nltk_data


def generate_geo_snippets(text, annotations):
    tokenizer = nltk.data.load('file:{}'.format(nltk_data('nl_punkt.pickle')))
    tree = IntervalTree.from_tuples(
        Interval(*posting, data=ann['districts'] + ann['neighborhoods'])
        for ann in annotations
        for posting in ann['postings']
    )
    snippets = []
    by_code = defaultdict(set)
    for span in tokenizer.span_tokenize(text):
        intervals = tree[slice(*span)]
        if intervals:
            # sentence overlaps with at least one posting
            snippet_index = len(snippets)
            h_snippet = u''
            cursor = span[0]
            for iv in sorted(intervals):
                h_snippet += text[cursor:iv.begin]
                h_snippet += u'<em class="c-details--toponym">{}</em>'.format(
                    text[iv.begin:iv.end]
                )
                cursor = iv.end
                for code in iv.data:
                    by_code[code].add(snippet_index)

            h_snippet += text[cursor:span[1]]
            snippets.append(
                h_snippet.replace('\n', ' ')
            )

    return snippets, by_code


def get_filtered_snippets(text, annotations, cbs_code=None):
    if not annotations or not text:
        return []

    snippets, by_code = generate_geo_snippets(text, annotations)

    if cbs_code:
        snippets = [
            snippets[i]
            for i in sorted(by_code[cbs_code])
        ]

    return snippets


def add_doc_snippets(doc_source, cbs_code=None, compact_sources=False):
    if doc_source.get('annotations'):
        doc_source['snippets'] = get_filtered_snippets(
            doc_source['description'],
            doc_source['annotations'],
            cbs_code
        )

    for source in doc_source.get('sources', []):
        if source.get('annotations'):
            source['snippets'] = get_filtered_snippets(
                source['description'],
                source['annotations'],
                cbs_code
            )

        if compact_sources is True:
            source.pop('annotations', None)
            source.pop('description', None)


def aggregate_toponyms(doc_source, cbs_code=None):
    def relevant_for_code(ann):
        if not cbs_code:
            return True
        elif cbs_code in ann.get('districts', []):
            return True
        elif cbs_code in ann.get('neighborhoods', []):
            return True
        else:
            return False

    root_toponyms = {
        ann['toponym']
        for ann in doc_source.get('annotations', [])
        if relevant_for_code(ann)
    }
    source_toponyms = {
        ann['toponym']
        for source in doc_source.get('sources', [])
        for ann in source.get('annotations', [])
        if relevant_for_code(ann)
    }

    return sorted(root_toponyms.union(source_toponyms))
