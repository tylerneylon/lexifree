#!/usr/bin/env python3
# coding: utf-8
''' evals.py

    This script helps to evaluate the quality of AI-generated dictionary
    entries. It expects that you've already run base_entries.py on a test set of
    words, so that it can load entries.json and find the AI-based entries to
    judge against wiktionary-based entries.

    Sample usage:

        # Run automatic evals.
        ./evals.py run test_N.json > results_N.json

        # Run a local server for human evals.
        ./evals.py serve results_N.json

        # Make a static eval html page to share results.
        ./evals.py html results_N.json > evals_N.html

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
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from tqdm import tqdm

import shotglass
import wiki


# ______________________________________________________________________
# OpenAI API functions

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
        print('Error via API call:', e, file=sys.stderr)
        return f"An error occurred: {e}"


# ______________________________________________________________________
# HTML utility functions

def get_red_to_green_hex_color(value):
    ''' This maps a value in [0, 1] to a dark color hex code, transitioning
    through red -> orange -> yellow -> green using the HSV color space.

    0.0 -> Red (#cc0000-ish)
    0.5 -> Yellow
    1.0 -> Green (#00cc00-ish) '''

    # For fully saturated colors that look "dark," we choose:
    hue = value * 100  # 0 is red, and 100 is a shade of green.
    sat = 1.0          # This is full saturation.
    val = 0.7          # Slightly reduce the brightness for a darker shade.

    # Convert HSV -> RGB.
    c = sat * val
    x = c * (1 - abs(((hue / 60) % 2) - 1))
    m = val - c
    if 0 <= hue < 60:
        r_p, g_p, b_p = c, x, 0
    elif 60 <= hue < 120:
        r_p, g_p, b_p = x, c, 0
    else:
        # This shouldn't happen for a hue in [0, 100], but just in case:
        r_p, g_p, b_p = 0, 0, 0

    # Shift to the final RGB by adding m.
    r = int((r_p + m) * 255)
    g = int((g_p + m) * 255)
    b = int((b_p + m) * 255)

    return f'#{r:02x}{g:02x}{b:02x}'

def remove_between(s, start_str, end_str):
    ''' This expects there to be a single instance of start_str, and a single
        instance of end_str, in s. This removes start_str, end_str, and
        everything between them from s, returning the result.
    '''
    before = s.split(start_str, 1)[0]
    after  = s.split(end_str,   1)[1]
    return before + after

def print_static_eval_page(results_file):
    test_file, results = load_results(results_file)
    html = make_eval_interface_html(test_file, results, static_page=True)
    print(html)


# ______________________________________________________________________
# Evaluation functions

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

def load_data(test_file, add_to_wiki_coverage=False):
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
    base_word_of = {}  # base_word_of[derived] = base
    with open('entries.json') as f:
        for line in f:
            data = json.loads(line)
            word = data['word']
            if 'error' in data:
                gpt_errors[word] = data['error']
            elif 'base_word' in data:
                base_word_of[word] = data['base_word']
            else:
                gpt_data[word] = data['entry']
                gpt_data[word]['version'] = data['version']

    # Load in the test entries.
    wiki_data = {}
    wiki_words = []  # Track the order of the words.
    words_not_in_wiki = set()
    with open(test_file) as f:
        for line in f:
            data = json.loads(line)
            word  = data['word']
            if 'error' in data:
                words_not_in_wiki.add(word)
                continue
            defns = data['wiktionary_definitions']
            wiki_data[word] = defns
            wiki_words.append(word)

    # We may have some base words that are defined by AI but not yet by wiki.
    # Attempt to add those wiki definitions now, if requested.
    if add_to_wiki_coverage:
        for word in base_word_of:
            if word in words_not_in_wiki:
                base_word = base_word_of[word]
                data = wiki.get_wiktionary_definitions(base_word)
                if data is None:  # Skip this word if it has no wiki definition.
                    continue
                with open(test_file, 'a') as f:
                    f.write(json.dumps(data) + '\n')
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

    # If the user generated a test set without making entries for it, then
    # wiki_data will be empty here, and that's an error for us.
    if len(wiki_data) == 0:
        def err_print(*s):
            print(*s, file=sys.stderr)
        err_print('\nError: No wiktionary data overlaps with entry data.')
        err_print('Did you forget to make entries for this test?')
        err_print('Exiting since I can\'t run evals without wiki data.\n')
        sys.exit(1)

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

    gpt_data, gpt_errors, wiki_data = load_data(
            test_file, add_to_wiki_coverage=True)
    print(json.dumps({'test_file': test_file}))

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
# Server functions

def make_word_eval_table(
        word, gpt_entry, wiki_defns, ai_matches, wiki_matches, static_page):
    ai_defns = gpt_entry['definitions']
    grid_style = f'grid-template-rows: repeat({2 * len(ai_defns) + 2}, auto)'
    parts = ['<div class="table-holder"><div class="table-left">']

    # Columns 1-3 are part of a grid-container.

    parts.append(f'<div class="grid-container" style="{grid_style}">')

    def add_item(body, classes=[], style=''):
        if type(classes) is str:
            classes = [classes]
        class_str = ' '.join(['grid-item'] + classes)
        parts.append(f'<div class="{class_str}" style="{style}">{body}</div>')

    # Column 1: The AI-based definitions.
    add_item(word, 'word')
    add_item('AI Definitions', 'subheader')
    for i, defn_obj in enumerate(ai_defns):
        defn = defn_obj['definition']
        add_item('', 'hrule', f'grid-row:{2 * i + 3}')
        add_item(f'<b>ai{i + 1}.</b> {defn}')
        # add_item(defn)

    # Column 2: Taste scores.
    add_item('Flavor Text', 'header')
    add_item('Flavor Score', 'subheader')
    unscored_str = 'unscored' if static_page else 'click to score'
    for i, defn_obj in enumerate(ai_defns):
        poetic_defn = '&lt;none&gt;'
        if 'poetic_definition' in defn_obj:
            poetic_defn = defn_obj['poetic_definition']
            attrs = {
                    'class': 'taste-score',
                    'data-word': word,
                    'data-ai-defn': i
            }
            attr_str = ' '.join(f'{key}="{val}"' for key, val in attrs.items())
            add_item(f'<div {attr_str}>{unscored_str}</div>\n' + poetic_defn)
        else:
            add_item(poetic_defn)

    # Column 3: Accuracy.
    add_item('Accuracy', 'header')
    add_item('Matches wiki defn?', 'subheader')
    for i, defn_obj in enumerate(ai_defns):
        match = ai_matches[i]
        text = 'no' if match is False else 'yes'
        text = f'<div class="match_{text}">{text}</div>'
        if not (match is False):
            text += f' matches:<br> <b>wiki{match + 1}.</b> {wiki_defns[match]}'
        add_item(text)

    parts.append('</div>')  # End of grid-container for columns 1-3.
    parts.append('</div>')  # End of table-left.

    # Column 4: Coverage.
    # This column is a peer with the above grid-container.

    parts.append('<div class="table-right">')
    grid_style = f'grid-template-rows: repeat({2 * len(wiki_defns) + 2}, auto);'
    grid_style += 'grid-template-columns: 1fr;'
    parts.append(f'<div class="grid-container" style="{grid_style}">')

    add_item('Wiktionary Coverage', 'header')
    add_item('Wiki defn is covered by an AI defn?', 'subheader')
    for i, wiki_defn in enumerate(wiki_defns):
        match = wiki_matches[i]
        text = 'no' if match is False else 'yes'
        text = f'<br><div class="match_{text} wiki_match">{text}</div>'
        if not (match is False):
            defn = ai_defns[match]['definition']
            text += f' matches:<br> <b>ai{match + 1}.</b> {defn}'
        add_item('', 'hrule', f'grid-row:{2 * i + 3}')
        add_item(f'<b>wiki{i + 1}.</b> ' + wiki_defn + text)

    parts.append('</div>')  # End of column 4's grid-container.
    parts.append('</div>')  # End of table-right.

    parts.append('</div>')  # End of table-holder.
    return '\n'.join(parts)

def load_results(results_file):
    with open(results_file) as f:
        first_line = next(f)
        test_file = json.loads(first_line)['test_file']
        results = [json.loads(line) for line in f]
    return test_file, results

def make_eval_interface_html(test_file, results, static_page=False):

    # Load in the word and definition data.
    gpt_data, gpt_errors, wiki_data = load_data(test_file)

    # Load in the html template.
    with open('templates/eval_results_template.html') as f:
        html = f.read()

    # Keep or remove the event listeners according to static_page.
    if static_page:
        html = remove_between(
                html, '$BEGIN_LISTENERS$', '$END_LISTENERS$'
        )
    else:
        html = html.replace('$BEGIN_LISTENERS$', '')
        html = html.replace('$END_LISTENERS$', '')

    # Load in the pre-existing taste scores, if any.
    taste_scores = {}
    for result in results:
        if 'taste_score' in result:
            key = result['word'] + result['ai_defn']
            taste_scores[key] = result['taste_score']
    # Aggregate the scores _after_ we've made `taste_scores`. Otherwise, we may
    # accidentally overcount journal entries that overlap each other.
    sum_taste_scores = 0
    num_taste_scores = 0
    for key, score in taste_scores.items():
        num_taste_scores += 1
        sum_taste_scores += score
    html = html.replace('$TASTE_SCORES$', str(taste_scores))

    # Build a table per word.
    words = {result['word'] for result in results}
    ai_matches, wiki_matches = {}, {}
    for result in results:
        if 'taste_score' in result:
            continue
        if 'ai_defn' in result:
            matches = ai_matches.setdefault(result['word'], {})
            matches[result['ai_defn']] = result['match']
        else:
            matches = wiki_matches.setdefault(result['word'], {})
            matches[result['wiki_defn']] = result['match']
    make_list = lambda x: [y[1] for y in sorted(x.items())]
    ai_matches   = { w: make_list(x) for w, x in ai_matches.items() }
    wiki_matches = { w: make_list(x) for w, x in wiki_matches.items() }
    html_parts = [
            make_word_eval_table(
                word, gpt_data[word], wiki_data[word],
                ai_matches[word], wiki_matches[word],
                static_page
            )
            for word in sorted(words)
    ]

    # Calculate the aggregate results.
    total_ai_defs  = 0
    total_accurate = 0
    for word in words:
        total_ai_defs  += len(gpt_data[word]['definitions'])
        total_accurate += len([x for x in ai_matches[word] if x is not False])
    accuracy = total_accurate / total_ai_defs

    total_wiki_defs = 0
    total_covered   = 0
    for word in words:
        total_wiki_defs += len(wiki_data[word])
        total_covered   += len([x for x in wiki_matches[word] if x is not
                                False])
    coverage = total_covered / total_wiki_defs

    if num_taste_scores == 0:
        taste = 'unknown'
    else:
        taste = sum_taste_scores / num_taste_scores

    # Insert a table of aggregate results at the top.
    if taste == 'unknown':
        st = '''background: linear-gradient(
            to right, #1e3c72, #2a5298, #76b2fe, #b69efe);
        '''
        taste_str = taste
        sub_str = 'no data yet'
    else:
        color = get_red_to_green_hex_color((taste - 1)/ 9)
        st = f'background-color: {color}'
        taste_str = f'{taste:5.2f}'
        sub_str = f'{num_taste_scores} taste score'
        if num_taste_scores > 1: sub_str += 's'
    tst_div = f'''
        <div class="top-result">Taste
            <div id="taste_score_avg" style="{st}" class="result-num">
                {taste_str}
            </div>
            <div id="taste_score_sub" class="result-sub">{sub_str}</div>
        </div>
    '''

    color = get_red_to_green_hex_color(accuracy)
    st = f'background-color: {color}'
    acc_div = f'''
        <div class="top-result">
            Accuracy
            <div style="{st}" class="result-num">{accuracy * 100:5.2f}%</div>
            <div class="result-sub">{total_ai_defs} AI definitions</div>
        </div>
    '''

    color = get_red_to_green_hex_color(coverage)
    st = f'background-color: {color}'
    n = total_wiki_defs
    cov_div = f'''
        <div class="top-result">
            Coverage
            <div style="{st}" class="result-num">{coverage * 100:5.2f}%</div>
            <div class="result-sub">{n} wiki definitions</div>
        </div>
    '''

    top_div = f'''<div class="centered top-results">
        {tst_div.strip()}{acc_div.strip()}{cov_div.strip()}
    </div>'''
    html_parts.insert(0, top_div)

    # Check which version we're working with.
    # We'll verify consistency and print a warning on multiple version strings.
    all_versions = Counter([
        gpt_data[w]['version'] for w in words
    ])
    version = list(all_versions.keys())[0]
    if len(all_versions.keys()) > 1:
        print('Warning: I see multiple version strings for this data:')
        print(all_versions)
        version = f'(mixed, ~{all_versions.most_common(1)})'
    html = html.replace('$VERSION$', version)

    # Compile and return the resulting html string.
    html = html.replace('$BODY$', '\n\n'.join(html_parts))
    return html

def make_main_page_handler(test_file, results):

    def get_page():
        # Rebuild this with each call since the `results` object may be updated
        # between calls.
        html = make_eval_interface_html(test_file, results)
        return html.encode('utf-8')

    return get_page

def make_update_handler(f, results):

    def handle_score_update(update):
        in_update_obj  = json.loads(update)
        out_update_obj = {
                'word': in_update_obj['word'],
                'ai_defn': in_update_obj['ai_defn'],
                'taste_score': in_update_obj['score']
        }
        f.write(json.dumps(out_update_obj) + '\n')
        f.flush()
        results.append(out_update_obj)
        return {'success': True}

    return handle_score_update

def serve_eval_interface(results_file):
    print('Go to http://localhost/ to use the interface.')
    print('Press ctrl-C when you\'re done to exit.')

    # Set up the route handlers.
    test_file, results = load_results(results_file)
    main_handler = make_main_page_handler(test_file, results)
    f = open(results_file, 'a')
    update_handler = make_update_handler(f, results)

    # Set up and run the server.
    GET_routes  = [['/', main_handler]]
    POST_routes = [['/score-update', update_handler]]
    shotglass.register_routes(GET_routes, POST_routes)
    shotglass.run_server()

    f.close()


# ______________________________________________________________________
# Main

if __name__ == '__main__':

    # Check the command-line arguments.
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(0)
    assert sys.argv[1] in ['run', 'serve', 'html']

    client = OpenAI()

    if sys.argv[1] == 'run':
        run_auto_evals(sys.argv[2])
    elif sys.argv[1] == 'serve':
        serve_eval_interface(sys.argv[2])
    elif sys.argv[1] == 'html':
        print_static_eval_page(sys.argv[2])

