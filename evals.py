#!/usr/bin/env python3
# coding: utf-8
''' evals.py

    This script helps to evaluate the quality of AI-generated dictionary
    entries. It expects that you've already run base_entries.py on a test set of
    words, so that it can load entries.json and find the AI-based entries to
    judge against wiktionary-based entries.

    Usage:

        ./evals.py run <test_set.json>      # Runs automatic evals.
        ./evals.py serve <result_set.json>  # Local server for human evals.
        ./evals.py html <result_set.json>   # Makes a static eval html page.

    In more detail:

    * The `run` command loads both entries.json as well as the given test json
      file. This prints, to stdout, a new set of json data (so you probably want
      to redirect it to a file) with the results of the evaluations that can be
      run without any human interaction.

    * The `serve` command starts a local http server so that you can
      hand-evaluate things that AI cannot auto-evaluate. For now, that means
      judging the poetic definitions (aka "flavor text") given for some entries.
      The results of your hand judgments are stored back into the same
      (modified) json file that you provide on the command line.

    * The `html` command expects that you've already run the above two commands,
      and it generates a new static html file that can be viewed to see a
      detailed summary of the evaluation results, which are broken down on a
      word-by-word basis so that mistakes can be easily understood.
'''


# ______________________________________________________________________
# Imports

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from tqdm import tqdm


# ______________________________________________________________________
# Functions

def get_gpt4o_response(prompt):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",

            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return completion
    except Exception as e:
        return f"An error occurred: {e}"

check_defn_prompt = '''
    Here are the official definitions for a particular word:

    $GIVEN_DEFNS$

    And here is an student's definition: "$DEFN$"

    Does the student's definition fit one of the official definitions above?
    If yes, answer with the number of the matching definition.
    If no, answer with the word no.
    Answer only with a number or the word no; no other words or marks at all.
'''

prompt_suffix = '''
    Be sure to only answer with either a number (of the matching definition) or
    with the word "no".
'''

def is_defn_good(defn, given_defns):
    ''' This expects `defn` to be a string, and given_defns to be a list of
        strings. This checks to see if `defn` matches one of the given defns.
        This returns False if `defn` is not in line with one of the given
        definitions; otherwise it returns an integer, which is the index of the
        matching given definition.'''
    for i in range(2):
        given_defns = '\n'.join([
            f'{i}. {defn}'
            for i, defn in enumerate(given_defns)
        ])
        subs = {
            '$GIVEN_DEFNS$': given_defns,
            '$DEFN$': defn
        }
        prompt = check_defn_prompt
        for key, value in subs.items():
            prompt = prompt.replace(key, value)
        if i > 0:
            prompt += prompt_suffix
        c = get_gpt4o_response(prompt)
        c = c.choices[0].message.content
        if c.lower() == 'no':
            return False
        if not all(char.isdigit() for char in c.strip()):
            continue
        return int(c.strip())

    return ('Error: bad GPT response', c)

def load_data(test_file):
    ''' This loads in test words from test_file (assumed to be a json file, with
        one json string per line), as well as the corresponding ai-made entries
        from entries.json.

        This returns the triple: gpt_data, gpt_errors, wiki_data.
        * gpt_data[word]   = <gpt entry for that word>
        * gpt_errors[word] = <error message for that word>
        * wiki_data[word]  = [list of wiki defns for that word]

        This also trims wiki_data to only keep the first-listed 100 words that
        are in gpt_data.
    '''
    assert test_file.endswith('.json')

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

    # Load in the test entries.
    wiki_data = {}
    wiki_words = []  # Track the order of the words.
    with open(test_file) as f:
        for line in f:
            data = json.loads(line)
            word  = data['word']
            defns = data['wiktionary_definitions']
            wiki_data[word] = defns
            wiki_words.append(word)

    # Reduce the word set down to the first 100 error-free words.
    keep = set()
    for word in wiki_words:
        if word in gpt_data:
            keep.add(word)
        if len(keep) == 100:
            break
    wiki_data = {w: value for w, value in wiki_data.items() if w in keep}

    return gpt_data, gpt_errors, wiki_data

def find_defn_matches(words, needles, needle_type, haystacks):
    ''' This expects the following three arguments to be lists whose elements
        correspond to each other:
        * words = the list of words being defined
        * needles = each item is a list of defns for the corresponding word
        * haystacks = each item is a list of defns for the corresponding word

        This also accepts:
        * needle_type = a str, describes the needles: 'ai_defn' or 'wiki_defn'

        This prints out json strings in the following format; they are expected
        to be redirected to a results file:
            {'word': word, '{ai,wiki}_defn': <int index>, 'match': 'no'|<int>}
        where the value of 'match' means either this needle had no match in the
        haystack (value 'no'), or indicates which haystack defn was a match.

        This returns the accuracy = the percent (in [0, 1]) of needle
        definitions that matched a corresponding haystack definition.
    '''

    def do_defn_check(word, defn_idx, defn, given_defns):
        result = is_defn_good(defn, given_defns)
        if type(result) is tuple:
            print(result[0], result[1], file=sys.stderr)
            print(f'  This is for defn {defn_idx} of "{word}"', file=sys.stderr)
            print(f'  Artifically marking as no-match', file=sys.stderr)
            result = False
        return {'word': word, needle_type: defn_idx, 'match': result}

    total = sum(len(defns) for defns in needles)
    num_mistakes = 0

    pbar = tqdm(total=total, file=sys.stderr)

    futures = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for word, check_defns, given_defns in zip(words, needles, haystacks):
            for i, defn in enumerate(check_defns):
                futures.append(executor.submit(
                    do_defn_check, word, i, defn, given_defns
                ))
        for future in as_completed(futures):
            eval_result = future.result()
            pbar.update(1)
            word = eval_result['word']
            pbar.set_description(f'{word:20s}')

            # This needs to be "is" because "0 == False" is True in Python.
            if eval_result['match'] is False:
                num_mistakes += 1

            print(json.dumps(eval_result))

    pbar.set_description('Done')
    pbar.close()

    accuracy = (total - num_mistakes) / total
    return accuracy

def run_auto_evals(test_file):
    ''' This reads word and definition data from test_file and entries.json, and
        then prints out json data with LLM-evaluated results on how good the
        test_file data is. In particular, this measures definition accuracy and
        definition coverage (similar to precision and recall).
    '''

    gpt_data, gpt_errors, wiki_data = load_data(test_file)

    # Check the accuracy of all the AI-based definitions that
    # correspond to test words. Keep in mind that gpt_data may contain
    # many more words than wiki_data, and we should ignore the extras.
    words = list(wiki_data.keys())

    # Form two corresponding definition lists.
    ai_defns = [
            [defn['definition'] for defn in gpt_data[w]['definitions']]
            for w in words
    ]
    wiki_defns = [wiki_data[w] for w in words]

    # Check that the AI definitions are good.
    accuracy = find_defn_matches(words, ai_defns, 'ai_defn', wiki_defns)
    print(f'AI defn accuracy: {accuracy * 100:.2f}%', file=sys.stderr)

    # Check that the wiki definitions are covered.
    coverage = find_defn_matches(words, wiki_defns, 'wiki_defn', ai_defns)
    print(f'AI defn coverage: {coverage * 100:.2f}%', file=sys.stderr)


# ______________________________________________________________________
# Main

if __name__ == '__main__':

    # Check the command-line arguments.
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(0)
    # TEMP TODO This script is only partially implemented right now.
    assert sys.argv[1] in ['run', 'serve']

    client = OpenAI()

    run_auto_evals(sys.argv[2])

