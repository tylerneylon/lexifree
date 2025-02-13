#!/usr/bin/env python3
# coding: utf-8
''' make_entries.py

    This script contains the main code to learn about core dictionary entry
    information for a given word. It is designed to be used as either a library,
    or as a command-line tool to quickly look up a subset of words.

    Command-line usage:

        ./make_entries.py START END

    The above will look up base dictionary entries for the words with indexes
    [START,END), both expected to be non-negative integers. These are indexes
    into the unigram dataset.

        ./make_entries.py <word_list.txt>

    The above will look up dictionary entries for the words listed, one per
    line, in the given file. (This relies on the extension .txt.)

        ./make_entries.py <word_list.json>
    
    The above will look up dictionary entries for the word objects (as JSON
    strings) listed in the given file. (This relies on the extension .json.)
    This expects one JSON object per line in the json file.

        ./make_entries.py -w WORD

    The above performs a lookup for WORD.

    TODO Add information on how to use this as a library.

    The unigram dataset was downloaded from here:

    https://www.kaggle.com/datasets/rtatman/english-word-frequency
'''


# ______________________________________________________________________
# Imports

import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

import google_defs


# ______________________________________________________________________
# Debug controls

do_print_defn_replacements = False


# ______________________________________________________________________
# Globals and Constants

# Use the format a.b only for officially-tagged releases; these should
# be single git hashes only. Otherwise use a format like a.b.c to help
# indicate work-in-progress. These may span multiple git hashes.
VERSION = '0.1.1'

PROMPT_TOKEN_COST = (2.5 / 1e6)     # That's $2.5 / 1m tokens.
COMPLETION_TOKEN_COST = (10 / 1e6)  # That's $ 10 / 1m tokens.


# ______________________________________________________________________
# Universal Initialization

# Things go here if they ought to be initialized whether or not this module is
# imported as a library, or run as main.

# Set up the OpenAI client connection.
client = OpenAI()


# ______________________________________________________________________
# Data Functions

def load_wordlist():
    ''' This loads all the words from unigram_freq.csv and returns them
        as a list of strings. '''

    print('Loading word list .. ', end='', flush=True)
    with open('unigram_freq.csv') as f:
        rows = list(csv.reader(f))
    # Drop the first header row, and the counts (row[1]) for each row.
    wordlist = [row[0] for row in rows[1:]]
    print('done.')

    return wordlist


# ______________________________________________________________________
# String functions

JACCARD_SIMILARITY_CUTOFF = 0.23

def get_bigrams(t):
    words = t.split()
    return [words[i] + ' ' + words[i + 1] for i in range(len(words) - 1)]

def are_texts_similar(t1, t2):
    bigrams1 = set(get_bigrams(t1))
    bigrams2 = set(get_bigrams(t2))
    similarity = len(bigrams1 & bigrams2) / len(bigrams1 | bigrams2)
    return similarity > JACCARD_SIMILARITY_CUTOFF


# ______________________________________________________________________
# OpenAI API Utilities

def get_gpt4o_response(prompt, cost=None, require_json=False):
    ''' Fetches a response from GPT-4o using the OpenAI API.
        Returns the response (a completion objection) from gpt-4o for the given
        `prompt`. If there's an error, an error message (a string) is returned
        instead.
        The optional `cost` parameter is expected to be a dict with a 'cost'
        key; this adds the cost (in dollars) to that value when `cost` is given.
        When require_json is True, the response is guaranteed to a JSON string.
    '''

    response_format = {'type': 'json_object'} if require_json else None

    try:
        completion = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': prompt}
            ],
            response_format=response_format
        )
        if cost:
            cost['cost'] += (
                    completion.usage.prompt_tokens * PROMPT_TOKEN_COST +
                    completion.usage.completion_tokens * COMPLETION_TOKEN_COST
            )
        return completion
    except Exception as e:
        print(e)
        return f'An error occurred: {e}'

def parse_json_from_reply(reply):
    ''' This expects `reply` to be a string that contains a JSON object or list.
        It pulls out the largest {}-contained or []-contained substring
        (whichever starts first), and attempts to parse that as JSON, returning
        the parsed object. '''
    start = reply.index('{')
    end   = reply.rindex('}') + 1
    if reply.index('[') < start:
        start = reply.index('[')
        end   = reply.rindex(']') + 1
    return json.loads(reply[start:end])


# ______________________________________________________________________
# Dictionary-specific LLM functions

def is_english_word(word, cost):
    c = get_gpt4o_response(
            f'Is "{word}" a word in English language? ' + 
            'Answer with only a yes or a no.',
            cost
    )
    reply = c.choices[0].message.content
    return 'yes' in reply.lower()

derived_check_template = '''
Is "$WORD$" a word that is a direct conjugation of another word?
For example, it may be a plural, a gerund, or a past tense version
of a root word.  Please reply with a JSON object like {"is_derived",
"root_word"}; the "root_word" key is optional; omit it if the word "$WORD$" is
not directly derived (such as a plural or past tense, etc). For borderline cases
like "educational" please say the word is not derived.'
'''

def check_if_derived(word, cost=None):
    ''' This returns (is_derived, root_word) for `word`.
        Examples: running -> True, 'run'
                  phone   -> False, None
    '''
    prompt = derived_check_template.replace('$WORD$', word)
    response = get_gpt4o_response(prompt, cost, require_json=True)
    data = json.loads(response.choices[0].message.content)
    is_derived = data['is_derived']
    root_word = data['root_word'] if is_derived else None
    return is_derived, root_word

dictionary_entry_prompt_template = '''
    Please provide a dictionary entry for the word "$WORD$" in JSON format.
    It should include each of these JSON keys:
    * word
    * part_of_speech
    * pronunciation
    * definitions - the value here is a list of objects with keys "definition"
      and "example"
    * origin
    * synonyms
    * antonyms
    The JSON string may include unicode characters, which is useful for the
    pronunciation key. Please produce only a JSON string with no decorations or
    other text.
'''

def get_dictionary_entry(word, cost):
    prompt = dictionary_entry_prompt_template.replace('$WORD$', word)
    c = get_gpt4o_response(prompt, cost)
    return c.choices[0].message.content

poetic_prompt_template = '''
    $DEFN$
    The above is a json list of base definitions for the word "$WORD$".
    Please add a new key "is_poetic" for each definition entry.
    Do not add new base definitions, or delete any. Do not edit the base
    definitions at all. Instead, only add entries per base definition.
    At first, only add the key "is_poetic" with a
    true/false value to indicate if this is poetry-worthy definition. Boring
    ideas or concepts are not poetic. Interesting words or ideas are.

    If a base definition is_poetic, then also add a new key "poetic_definition"
    for each definition entry.
    Aim to write each new poetic definition in the style of a novelist or
    creative and liberal professor of language arts. Aim for a definition
    that is not too long but also almost inspiring and fun in its expression.
    Each poetic definition should be short.

    Please reply only with a JSON string, no other text.
'''

def add_poetic_definitions(json_entry, cost):
    word = json_entry['word']
    defns = json.dumps(json_entry['definitions'])
    prompt = poetic_prompt_template.replace('$WORD$', word)
    prompt = prompt.replace('$DEFN$', defns)
    c = get_gpt4o_response(prompt, cost)
    return c.choices[0].message.content

rephrase_prompt_template = '''
Below is a definition for the word "$WORD$":

$DEFN$

Can you please rephrase this definition, keeping the meaning the same? My only
goal is to avoid a copyright violation because this phrasing is too similar to
someone else's definition. Keep the meaning the same, but significantly alter
the wording. Reply with only the new definition and nothing else.
'''

def rephrase_definition(word, old_def, cost):
    prompt = rephrase_prompt_template
    prompt = prompt.replace('$WORD$', word)
    prompt = prompt.replace('$DEFN$', old_def)
    c = get_gpt4o_response(prompt, cost)
    return c.choices[0].message.content

def build_entry(word, f=None):
    ''' This creates a new entry object for `word`, and returns that entry.
        The entry will be in one of these formats:

        * {'word', 'error': string} OR
        * {'word', 'base_word'} OR
        * {'word', 'entry'}

        If a file pointer is provided in f, then the entry will be written to f
        as well; this is intended to be used when f is in append mode on a file
        with one json string per line. (This function writes one line, including
        a terminating newline, to that file.)
    '''

    log_entry = {'word': word, 'version': VERSION}
    gpt_cost  = {'cost': 0}

    def save_progress():
        log_entry['cost'] = gpt_cost['cost']
        if f is not None:
            f.write(json.dumps(log_entry) + '\n')

    # Currently the code ignores is_ok, but you can add that back in if you'd
    # like (as part of a return value).
    def finish(is_ok):
        save_progress()
        return log_entry

    # Check to see if this is a valid English word.
    if not is_english_word(word, gpt_cost):
        log_entry['error'] = 'not an English word'
        return finish(False)

    is_derived, base_word = check_if_derived(word, gpt_cost)
    if is_derived:
        log_entry['base_word'] = base_word
        save_progress()
        return build_entry(base_word, f)

    # Get the initial entry.
    reply = get_dictionary_entry(word, gpt_cost)
    entry = parse_json_from_reply(reply)

    if False:
        print('Initial entry:')
        print(json.dumps(entry, indent=4))

    if not (type(entry) is dict):
        log_entry['error'] = 'Initial entry was not a dict object'
        return finish(False)

    # Check for potential copyright problems.
    g_defs = google_defs.lookup(word)
    if g_defs is not None:
        for i, ai_def_obj in enumerate(entry['definitions']):
            ai_def = ai_def_obj['definition']
            for g_def in g_defs:
                if are_texts_similar(g_def, ai_def):
                    new_def = rephrase_definition(word, ai_def, gpt_cost)
                    entry['definitions'][i]['definition'] = new_def
                    if do_print_defn_replacements:
                        print('Problem found:')
                        print('AI definition    :', ai_def)
                        print('Google definition:', g_def)
                        print('Replacing that with new definition:', new_def)

    log_entry['entry'] = entry

    # Add poetic definitions.
    reply = add_poetic_definitions(entry, gpt_cost)
    poetic_json = parse_json_from_reply(reply)

    if False:
        print('poetic_json:')
        print(json.dumps(poetic_json, indent=4))

    if not (type(poetic_json) is list):
        log_entry['error'] = 'Poetic definitions were not a list object'
        return finish(False)

    poetic_key = 'poetic_definition'
    for i, poetic in enumerate(poetic_json):
        if poetic_key in poetic:
            entry['definitions'][i][poetic_key] = poetic[poetic_key]

    # Save out successful dictionary entry.
    return finish(True)


# ______________________________________________________________________
# Main

if __name__ == '__main__':

    def print_docs_and_exit():
        print(__doc__)
        sys.exit(0)

    # Check the command-line arguments.
    if len(sys.argv) < 2:
        print_docs_and_exit()

    # Parse the command-line arguments.
    if sys.argv[1] == '-w':
        if len(sys.argv) < 3:
            print_docs_and_exit()
        words = [sys.argv[2]]
    elif sys.argv[1].endswith('.txt'):
        with open(sys.argv[1]) as f:
            words = [line.strip() for line in f]
    elif sys.argv[1].endswith('.json'):
        with open(sys.argv[1]) as f:
            words = [
                    json.loads(line)['word']
                    for line in f
            ]
    elif len(sys.argv) < 3:
        print_docs_and_exit()
    else:
        start = int(sys.argv[1])
        end   = int(sys.argv[2])
        assert 0 <= start < end
        wordlist = load_wordlist()  # Load our word list.
        words = wordlist[start:end]

    # If there's only one word, don't be fancy about it.
    pbar = None
    if len(words) == 1:
        with open('entries.json', 'a') as f:
            build_entry(words[0], f)
        sys.exit(0)

    # Get dictionary data for the given words.
    pbar = tqdm(total=len(words), file=sys.stderr)
    with open('entries.json', 'a') as f:
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                    executor.submit(build_entry, word, f)
                    for word in words
            ]
            for future in as_completed(futures):
                entry = future.result()
                pbar.update(1)
                pbar.set_description(entry['word'])
    pbar.set_description('Done')
