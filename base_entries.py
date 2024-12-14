#!/usr/bin/env python3
# coding: utf-8
''' base_entries.py

    This script contains the main code to learn about core dictionary entry
    information for a given word. It is designed to be used as either a library,
    or as a command-line tool to quickly look up a subset of words.

    Command-line usage:

        ./base_entries.py START END

    The above will look up base dictionary entries for the words with indexes
    [START,END), both expected to be non-negative integers. These are indexes
    into the unigram dataset.

        ./base_entries.py <word_list.txt>

    The above will look up dictionary entries for the words listed, one per
    line, in the given file. (This relies on the extension .txt.)

        ./base_entries.py <word_list.json>
    
    The above will look up dictionary entries for the word objects (as JSON
    strings) listed in the given file. (This relies on the extension .json.)
    This expects one JSON object per line in the json file.

        ./base_entries.py -w WORD

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


# ______________________________________________________________________
# Globals and Constants

VERSION = '0.1'

gpt_cost = 0
PROMPT_TOKEN_COST = (2.5 / 1e6)     # That's $2.5 / 1m tokens.
COMPLETION_TOKEN_COST = (10 / 1e6)  # That's $ 10 / 1m tokens.


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
# OpenAI API Utilities

def get_gpt4o_response(prompt):
    ''' Fetches a response from GPT-4o using the OpenAI API.
        Returns the response (a completion objection) from gpt-4o for the given
        `prompt`. If there's an error, an error message (a string) is returned
        instead.
    '''
    global gpt_cost
    try:
        completion = client.chat.completions.create(
            model='gpt-4o',

            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': prompt}
            ]
        )
        gpt_cost += (
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

def is_english_word(word):
    c = get_gpt4o_response(
            f'Is "{word}" a word in English language? ' + 
            'Answer with only a yes or a no.'
    )
    reply = c.choices[0].message.content
    return 'yes' in reply.lower()

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

def get_dictionary_entry(word):
    prompt = dictionary_entry_prompt_template.replace('$WORD$', word)
    c = get_gpt4o_response(prompt)
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

def add_poetic_definitions(json_entry):
    word = json_entry['word']
    defns = json.dumps(json_entry['definitions'])
    prompt = poetic_prompt_template.replace('$WORD$', word)
    prompt = prompt.replace('$DEFN$', defns)
    c = get_gpt4o_response(prompt)
    return c.choices[0].message.content

def log_entry_for_word(word, f):
    ''' Appends a line to the open file at f; this line
        contains a JSON string in one of the following formats:
        * {'word', 'error': string} OR
        * {'word', 'base_word'} OR
        * {'word', 'entry'}

        Returns True on success and False if there was any problem.
    '''
    global gpt_cost

    log_entry = {'word': word, 'version': VERSION}

    gpt_cost = 0
    def finish(return_value):
        log_entry['cost'] = gpt_cost
        f.write(json.dumps(log_entry) + '\n')
        return return_value

    # Check to see if this is a valid English word.
    if not is_english_word(word):
        log_entry['error'] = 'not an English word'
        return finish(False)

    # Get the initial entry.
    reply = get_dictionary_entry(word)
    entry = parse_json_from_reply(reply)

    if False:
        print('Initial entry:')
        print(json.dumps(entry, indent=4))

    if not (type(entry) is dict):
        log_entry['error'] = 'Initial entry was not a dict object'
        return finish(False)

    log_entry['entry'] = entry

    # Add poetic definitions.
    reply = add_poetic_definitions(entry)
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

    # Set up the OpenAI client connection.
    client = OpenAI()

    # Get dictionary data for the given words.
    if len(words) > 1:
        pbar = tqdm(total=len(words), file=sys.stderr)
    with open('entries.json', 'a') as f:
        for word in words:
            pbar.set_description(word)
            # print(f'Building the entry for "{word}"')
            log_entry_for_word(word, f)
            pbar.update(1)
