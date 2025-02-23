#!/usr/bin/env python3
# coding: utf-8
''' wiki.py

    This small library assists with wiktionary definition lookups.

    Usage:

        import wiki

        defn_obj = wiki.get_wiktionary_definitions(my_word)

        if defn_obj is None:
            handle_error()
        else:
            for defn in defn_obj['wiktionary_definitions']:
                use_defn(defn)

'''


# ______________________________________________________________________
# Imports

import json
import sys
from urllib import request
from bs4 import BeautifulSoup


# ______________________________________________________________________
# Constants

WIKTIONARY_URL_TEMPLATE = (
        'https://en.wiktionary.org/api/rest_v1/page/definition/' +
        '$WORD$?redirect=false'
)


# ______________________________________________________________________
# Internal functions

def _starts_lower(s):
    return s[0].islower()

def _capitalize(s):
    return ''.join([s[0].upper()] + list(s[1:]))

def _err_print(*s):
    print(*s, file=sys.stderr)

# ______________________________________________________________________
# Public functions

def get_wiktionary_definitions(word, verbose=True):
    ''' This looks up and parses definitions for `word` in wiktionary.
        On success, it returns an object of this shape:
            {'word': str, 'wiktionary_definitions': [str]}
        If the original input `word` fails, this also attempts to look up the
        same word with the first letter capitalized.
        If there's an error, it returns None.
    '''
    # print(f'Looking up the definitions for "{word}" .. ', end='', flush=True)
    url = WIKTIONARY_URL_TEMPLATE.replace('$WORD$', word)
    # print('url', url)
    try:
        with request.urlopen(url) as response:
            data = response.read().decode('utf-8')
    except:
        if verbose:
            _err_print(f'Error looking up the word "{word}"')
        if _starts_lower(word):
            return get_wiktionary_definitions(_capitalize(word), verbose)
        return None
    data_obj = json.loads(data)
    defns = []
    if 'en' not in data_obj:
        if verbose:
            _err_print(f'Error: no "en" block for the word "{word}"')
        if _starts_lower(word):
            return get_wiktionary_definitions(_capitalize(word))
        return None
    for defn_block in data_obj['en']:
        # Uncomment this to help with debugging.
        if False:
            print('_' * 70)
            print('defn_block:')
            print(defn_block)
            print()
        part_of_speech = defn_block['partOfSpeech']
        for defn in defn_block['definitions']:
            defn_text = defn['definition']
            if len(defn_text.strip()) == 0:
                continue
            # Skip over entries that act as references.
            if 'mw-cite-backlink' in defn_text:
                continue
            soup = BeautifulSoup(defn_text, 'html.parser')
            defns.append(part_of_speech + ' ' + soup.get_text())
    # print('done.')
    return {'word': word, 'wiktionary_definitions': defns}
