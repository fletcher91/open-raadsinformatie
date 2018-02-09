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
    by_code = defaultdict(lambda: defaultdict(list))
    for span in tokenizer.span_tokenize(text):
        intervals = tree[slice(*span)]
        if intervals:
            # sentence overlaps with at least one posting
            snippet_index = len(snippets)
            for iv in sorted(intervals):
                for code in iv.data:
                    by_code[code][snippet_index].append(
                        (iv.begin - span[0], iv.end - span[0])
                    )

            raw_snippet = text[slice(*span)].replace('\n', ' ')
            snippets.append(raw_snippet)

    return snippets, by_code


def highlight_snippet(raw_snippet, postings):
    h_snippet = u''
    cursor = 0
    for begin, end in postings:
        if begin >= cursor:
            h_snippet += raw_snippet[cursor:begin]
            h_snippet += u'<em class="c-details--toponym">{}</em>'.format(
                raw_snippet[begin:end]
            )
            cursor = end

    h_snippet += raw_snippet[cursor:]
    return h_snippet


def get_filtered_snippets(text, annotations, cbs_code=None):
    if not annotations or not text:
        return []

    snippets, by_code = generate_geo_snippets(text, annotations)

    if cbs_code:
        snippets = [
            highlight_snippet(snippets[i], postings)
            for i, postings in sorted(by_code[cbs_code].iteritems())
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
