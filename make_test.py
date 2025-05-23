#!/usr/bin/env python3
# coding: utf-8
''' make_test.py

    This script creates test cases that can be used to help evaluate the quality
    of an AI-based dictionary.

    Command-line usage:

        ./make_test.py NUM_WORDS [-w] [-s SEED]

    This will print out (to stdout) a list of NUM_WORDS different English words
    or common strings (such as names or typos) based on the unigram_freq.csv
    file, which is itself based on Google's public ngram data from many
    English-language books.

    If -w is included, then each line is a stringified JSON object with these
    keys:
    * word: the word itself
    * wiktionary_definitions: a list of strings, each string being a
    part-of-speech and the text of a definition from wiktionary. (The "w" in
    "-w" stands for wiktionary.)

    If -w is excluded, then each line is just a word, with no JSON syntax or
    anything else. I would recommend redirecting this output to a txt file.

    If -s SEED is included, then SEED is used as the random number generator's
    seed value. If -s is not included, then the seed is printed to stderr. This
    enables reproducability.
'''


# ______________________________________________________________________
# Imports

import csv
import json
import math
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

import wiki


# ______________________________________________________________________
# Constants

MIN_WORD_INDEX =   1_000
MAX_WORD_INDEX = 100_000

WIKTIONARY_URL_TEMPLATE = (
        'https://en.wiktionary.org/api/rest_v1/page/definition/' +
        '$WORD$?redirect=false'
)

# ______________________________________________________________________
# Functions

def parse_seed_from_args(args):
    ''' This returns `seed` and modifies `args` to exclude the -s SEED values,
        if they were provided.  If no seed was given, a random seed value is
        returned using random.randint().
    '''
    seed = random.randint(1, 100_000)
    to_del = None
    for i, arg in enumerate(args[:-1]):
        if arg == '-s':
            seed = int(args[i + 1])
            to_del = i
            break
    if to_del:
        del args[to_del]
        del args[to_del]  # Twice to get both -s and SEED.
    return seed


# ______________________________________________________________________
# Main

if __name__ == '__main__':

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    num_words = int(sys.argv[1])
    do_use_wiktionary = ('-w' in sys.argv)

    # Express the seed so we can support reproducability.
    seed = parse_seed_from_args(sys.argv)
    random.seed(seed)
    print(f'Using the seed {seed}.', file=sys.stderr)

    # Load in the unigram frequency data.
    with open('unigram_freq.csv') as f:
        rows = list(csv.reader(f))

    candidates = rows[MIN_WORD_INDEX:MAX_WORD_INDEX]
    candidate_words, candidate_weights = list(zip(*candidates))
    candidate_weights = [float(w) for w in candidate_weights]

    # Oversample because, when looking things up in wiktionary, some
    # words from unigram_freq.csv may not be defined.
    rand_words = random.choices(
            candidate_words,
            weights=candidate_weights,
            k=math.ceil(num_words)
    )

    if not do_use_wiktionary:
        for word in rand_words:
            print(word)
        sys.exit(0)

    progress_bar = tqdm(total=num_words, file=sys.stderr)
    error_words = set()

    def get_test_entry(word):
        word_obj = wiki.get_wiktionary_definitions(word, verbose=False)
        if word_obj is None:
            word_obj = {'word': word, 'error': 'wiki lookup failed'}
        return word_obj

    with ThreadPoolExecutor(max_workers=200) as executor:
        futures = [
                executor.submit(get_test_entry, word)
                for word in rand_words
        ]
        for future in as_completed(futures):
            test_entry = future.result()
            if 'error' in test_entry:
                error_words.add(test_entry['word'])
            print(json.dumps(test_entry))
            progress_bar.update(1)

    progress_bar.close()
    if len(error_words) > 0:
        print('The following words were not in wiktionary', error_words,
              file=sys.stderr)
    
