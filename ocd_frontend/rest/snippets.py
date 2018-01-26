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
            for iv in intervals:
                for code in iv.data:
                    by_code[code].add(snippet_index)

            snippets.append(
                text[slice(*span)].replace('\n', ' ')
            )

    return snippets, by_code


def get_snippets_for_area(snippets, by_code, code):
    return [
        snippets[i]
        for i in sorted(by_code[code])
    ]
