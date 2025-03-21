#!/usr/bin/env python3
# coding: utf-8
''' tools.py

    This script contains general tools to simplify working with the primary
    lexifree modules, such as make_entries.py.

    In general, you use this script like so:

        ./tools.py <command> [any command-specific options]

    Here's a brief summary of all commands:

        ./tools.py reversion [new-version-string]  # Update vers. in entries.
        ./tools.py lookup [word]                   # Print `word`'s entry.

    ______________________________________________________________________
    Here are more details on each command:

        ./tools.py reversion [new-version-string]

    The above will edit entries.json, updating all version strings into the
    new-version-string. This command is useful when you've tested out a new
    iteration of the entry-creation system, and you'd like to archive the most
    recent results as the tests that indicated this is an improvement over the
    previous iteration. Two notes:

    * The new-version-string should not start with "v". E.g.: "1.2" not "v1.2".
    * No version strings are stored in test_N.json or results_N.json, so there
      is no need to edit those files. Only entries.json needs to be updated.
    * You'll want to reversion the entries _before_ you save the results by
      running `evals.py html`.

        ./tools.py lookup [word]

    The above will look up the entry for `word` in entries.json and print out
    the result.
'''


# ______________________________________________________________________
# Imports

import json
import sys
from itertools import chain


# ______________________________________________________________________
# Public functions

def load_entry_data(style='raw'):
    ''' This loads in and indexes the data in entries.json. It returns:
            entries, redirects, errors
        If style is 'raw':
            All full log entries are in `entries`, which is a list.
            `redirects` and `errors` are both None.
        If style is 'indexed':
            `entries` is a dict mapping words to their dictionary entries.
            `redirects` is a dict mapping words to their base words.
            `errors` is a dict mapping words to their error messages.
    '''
    # TODO: Implement the 'indexed' version and use that elsewhere, including in
    #       check_entry.

    # Basic input-checking.
    assert style in ['raw', 'indexed']

    # Load in the AI-based entries.
    entries, redirects, errors = [], None, None
    if style == 'indexed':
        entries, redirects, errors = {}, {}, {}
    with open('entries.json') as f:
        for line in f:
            data = json.loads(line)
            if style == 'raw':
                entries.append(data)
            elif style == 'indexed':
                word = data['word']
                if 'error' in data:
                    errors[word] = data['error']
                elif 'base_word' in data:
                    redirects[word] = data['base_word']
                else:
                    entries[word] = data['entry']
    return entries, redirects, errors


# ______________________________________________________________________
# Internal functions

def update_version_to(version_str):

    # Load in the current data.
    entries, _, _ = load_entry_data(style='raw')

    # Modify all the version data.
    # This function expects version_str to exclude a starting "v",
    # and this is a consistent convention in this codebase.
    with open('entries.json', 'w') as f:
        for entry in entries:
            entry['version'] = version_str
            f.write(json.dumps(entry) + '\n')
    print('Done!')

def did_find_cased_word(word, entries, redirects, errors):
    # Try to find the word.
    if word in entries:
        print('Entry:')
        print(json.dumps(entries[word], indent=4))
        return True
    elif word in redirects:
        print(f'Redirect:\n  base_word={redirects[word]}')
        return True
    elif word in errors:
        print('Error info:')
        print(json.dumps(errors[word], indent=4))
        return True
    return False

def lookup_word(word):
    # Load the current data.
    entries, redirects, errors = load_entry_data(style='indexed')

    # Give first preference for the capitalization of the user.
    if not did_find_cased_word(word, entries, redirects, errors):
        # See if there's an adjusted capitalization we can find instead.
        all_keys = chain(entries.keys(), redirects.keys(), errors.keys())
        capitalization = {w: w.lower() for w in all_keys}
        if word.lower() in capitalization:
            word = capitalization[word.lower()]
            did_find_cased_word(word, entries, redirects, errors)
        else:
            print(f'Couldn\'t find {word} in entries.json.')


# ______________________________________________________________________
# Main

if __name__ == '__main__':

    def print_docs_and_exit():
        print(__doc__)
        sys.exit(0)

    if len(sys.argv) < 2:
        print_docs_and_exit()

    if sys.argv[1] == 'reversion':
        if len(sys.argv) < 3:
            print_docs_and_exit()
        version_str = sys.argv[2]
        if version_str.startswith('v'):
            print('Error: Please don\'t start your version string with v.')
            sys.exit(0)
        update_version_to(version_str)
    elif sys.argv[1] == 'lookup':
        if len(sys.argv) < 3:
            print_docs_and_exit()
        lookup_word(sys.argv[2])
    else:
        print(f'Unrecognized command: {sys.argv[1]}')
        sys.exit(0)
