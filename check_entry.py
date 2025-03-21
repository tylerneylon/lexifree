#!/usr/bin/env python3
# coding: utf-8
''' check_entry.py

    This script is a small utility to look up the entry of a single word.

    Sample usage:

        ./check_entry.py success  # Pretty prints the entry for "success".
'''
# TODO: Merge this functionality all into tools.py.


# ______________________________________________________________________
# Imports

import json
import sys
from itertools import chain


# ______________________________________________________________________
# Functions

def load_entry_data():
    ''' This loads in and indexes the data in entries.json. It returns:
            gpt_data, gpt_errors
        so that:
            gpt_data[word]  = <the entry for `word`>
            gpt_error[word] = <the error message for `word`>
    '''
    # Load in the AI-based entries.
    gpt_data = {}
    gpt_errors = {}
    with open('entries.json') as f:
        for line in f:
            data = json.loads(line)
            word = data['word']
            if 'error' in data:
                gpt_errors[word] = data['error']
            else:
                gpt_data[word] = data['entry']

    return gpt_data, gpt_errors


# ______________________________________________________________________
# Main

if __name__ == '__main__':

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    word = ' '.join(sys.argv[1:]).lower()

    gpt_data, gpt_errors = load_entry_data()
    all_keys = chain(gpt_data.keys(), gpt_errors.keys())
    capitalization = {w: w.lower() for w in all_keys}

    key = capitalization.get(word, word)

    if key in gpt_data:
        print('Entry:')
        print(json.dumps(gpt_data[key], indent=4))

    if key in gpt_errors:
        print('Error info:')
        print(json.dumps(gpt_errors[key], indent=4))

    if (key not in gpt_data) and (key not in gpt_errors):
        print(f'No entry or error found for "{word}" (case-insensitive)')
