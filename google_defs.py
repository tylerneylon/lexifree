#!/usr/bin/env python3
# coding: utf-8
''' google_defs.py

    This script provides a cached lookup of Google's definitions for words.

    Usage:

        import google_defs

        defs = google_defs.lookup(word)

    The return value of google_defs.lookup() will either be None (if there was
    an error), or a list of strings, which are the definitions.

    This module automatically uses and adds to the local file google_defs.json,
    which has one json string per line in this format:

        {'word': str, 'definitions': [str]}

    This module will never refresh a word already in the cache; it will act as
    if that definition list is good forever. In terms of capitalization, this
    module will preserve the capitalization that is handed to it in the
    `lookup()` calls.
'''


# ______________________________________________________________________
# Imports

import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ______________________________________________________________________
# Debug controls

do_print_cache_status = False

def dbg_print(*s):
    if not do_print_cache_status:
        return
    print(*s)


# ______________________________________________________________________
# Globals and Constants

# These are initialized below.
cache_file = None
known_defs = None

URL_PREFIX = 'https://googledictionary.freecollocation.com/meaning?word='


# ______________________________________________________________________
# Public interface

def lookup(word):

    if word in known_defs:
        dbg_print(f'google_defs: used cache for "{word}"')
        return known_defs[word]

    dbg_print(f'google_defs: looking up from web: "{word}"')
    url = URL_PREFIX + word
    response = requests.get(url)
    defs = _extract_definitions(response.text)

    if len(defs) == 0:
        return None

    json_str = json.dumps({'word': word, 'definitions': defs})
    cache_file.write(json_str + '\n')
    known_defs[word] = defs

    return defs


# ______________________________________________________________________
# Private interface

def _extract_definitions(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Locate the section containing definitions
    definition_list = []
    for ol in soup.find_all('ol'):
        div = ol.find('div')
        for li in div.find_all('li'):
            # Ensure we stop at "Web Definitions:"
            if li.find_previous('h2', string="Web Definitions:"):
                return definition_list

            # Extract text content
            if li['style'] == 'list-style:decimal':
                definition_text = str(list(li.children)[0]).strip()
                definition_list.append(definition_text)

    return definition_list


# ______________________________________________________________________
# Initialization

cache_file_path = Path('google_defs.json')

if not cache_file_path.exists():
    cache_file_path.touch()

known_defs = {}
with open(cache_file_path) as f:
    for line in f:
        def_data = json.loads(line)
        known_defs[def_data['word']] = def_data['definitions']

cache_file = open(cache_file_path, 'a')
