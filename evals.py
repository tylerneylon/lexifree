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

from openai import OpenAI


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
        return completion.choices[0].message
    except Exception as e:
        return f"An error occurred: {e}"

check_defn_prompt = '''
    Here are the official definitions for a particular word:

    $WIKI_DEFNS$

    And here is an student's definition: "$AI_DEFN$"

    Does the student's definition fit one of the official definitions above?
    Only answer with a yes or no, no quote marks or any other words or marks.
'''

def is_ai_defn_good(word, ai_defn, wiki_defns):
    ''' This expects three strings: a word, an ai definition, and a stringified
        list of wiktionary definitions. This returns True iff the ai definition
        is deemed (by AI) to be in line with one of the wiki definitions. '''
    subs = {
        '$WORD$': word,
        '$WIKI_DEFNS$': wiki_defns,
        '$AI_DEFN$': ai_defn
    }
    prompt = check_defn_prompt
    for key, value in subs.items():
        prompt = prompt.replace(key, value)
    c = get_gpt4o_response(prompt)
    return c.choices[0].message.content.lower() == 'yes'

def run_auto_evals(test_file):

    assert test_file.endswith('.json')

    # Load in the AI-based entries.
    gpt_data = {}
    error_words = {}
    with open('entries.json') as f:
        for line in f:
            data = json.loads(line)
            word = data['word']
            if 'error' in data:
                error_words[word] = data['error']
            else:
                gpt_data[word] = data['entry']

    # Load in the test entries.
    wiki_data = {}
    with open(test_file) as f:
        for line in f:
            data = json.loads(line)
            word  = data['word']
            defns = data['wiktionary_definitions']
            wiki_data[word] = defns

    # TODO Factor out data loading and a filtering step where we
    #      narrow down to the first 100 non-error words.

    eval_results = {}

    # Check the accuracy of all the AI-based definitions that
    # correspond to test words. Keep in mind that gpt_data may contain
    # many more words than wiki_data, and we should ignore the extras.
    words = list(wiki_data.keys())[:2]
    for word in words:
        if word in error_words:
            error = error_words[word]
            print(f'Skipping "{word}" due to error: {error}')
            continue
        wiki_defns = '\n'.join(wiki_data[word])
        ai_defn_results = []
        for ai_defn in gpt_data[word]['definitions']:
            is_ok = is_ai_defn_good(word, ai_defn['definition'], wiki_defns)
            ai_defn_results.append(is_ok)
        eval_results[word] = ai_defn_results

    print(json.dumps(eval_results))


# ______________________________________________________________________
# Main

if __name__ == '__main__':

    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(0)

    # TEMP TODO This script is only partially implemented right now.
    assert sys.argv[1] == 'run'

    client = OpenAI()

    run_auto_evals(sys.argv[2])

