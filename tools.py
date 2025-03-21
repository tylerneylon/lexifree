#!/usr/bin/env python3
# coding: utf-8
''' tools.py

    This script contains general tools to simplify working with the primary
    lexifree modules, such as make_entries.py.

    In general, you use this script like so:

        ./tools.py <command> [any command-specific options]

    Here are all the commands available:

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
'''


# ______________________________________________________________________
# Imports

import json
import sys


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

    # Load in the AI-based entries.
    entries, redirects, errors = [], None, None
    with open('entries.json') as f:
        for line in f:
            data = json.loads(line)
            entries.append(data)
            # word = data['word']
            # if 'error' in data:
            #     ai_errors[word] = data['error']
            # elif 'base_word' in data:
            #     ai
            # else:
            #     ai_data[word] = data['entry']
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
    else:
        print(f'Unrecognized command: {sys.argv[1]}')
        sys.exit(0)
