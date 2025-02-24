#!/usr/bin/env python3
# coding: utf-8
''' make_pages.py

    This script makes html pages for the dictionary entries in entries.json.

    Command-line usage:

        ./make_pages.py  # No command-line parameters!

    This will read data from entries.json and create one html page per entry in
    the html/ directory.
'''

# TODO: If this script ends up taking a few seconds or longer, add a tqdm
#       progress bar so the user knows what's up.


# ______________________________________________________________________
# Imports

import json


# ______________________________________________________________________
# Globals and Constants

html_template = None


# ______________________________________________________________________
# Functions

single_defn_template = '''
        <div class="definition-row">
            <div class="left-col">
                <div class="definition-block">
                    <strong>$DEFINITION$</strong>
                    <div class="example">
                        $EXAMPLE$
                    </div>
                </div>
            </div>
            <div class="right-col">
            $POETIC_BLOCK$
            </div>
        </div>
'''

poetic_defn_template = '''
                <div class="flavor-block">
                    <div class="placeholder-image">
                        <span>🪶</span>
                    </div>
                    <div class="poetic-text">
                        $POETIC_DEFINITION$
                    </div>
                </div>
'''

# TODO: If any of these are missing from the entry, drop the section entirely
#       rather than having a header with nothing below it.
entry_endnote_template = '''
        <div class="origin-synonyms">
            <div class="end-div">
                <div class="label">ORIGIN</div>
                $ORIGIN$
            </div>
            <div class="end-div">
                <div class="label">SYNONYMS</div>
                $SYNONYMS$
            </div>
            <div class="end-div">
                <div class="label">ANTONYMS</div>
                $ANTONYMS$
            </div>
        </div>
'''

def make_page_for_entry(word, entry):

    html = html_template
    html = html.replace('$WORD$', word)

    # Set up the pronunciation.
    pronun = entry['pronunciation']
    if not pronun.startswith('/'):
        pronun = f'/{pronun}/'
    html = html.replace('$PRONUNCIATION$', pronun)

    # Set up the definitions.
    defn_strs = []
    for defn_obj in entry['definitions']:
        defn_str = single_defn_template
        defn_str = defn_str.replace('$DEFINITION$', defn_obj['definition'])
        defn_str = defn_str.replace('$EXAMPLE$', defn_obj['example'])
        if 'poetic_definition' in defn_obj:
            poetic_block = poetic_defn_template
            poetic_block = poetic_block.replace('$POETIC_DEFINITION$',
                                                defn_obj['poetic_definition'])
            defn_str = defn_str.replace('$POETIC_BLOCK$', poetic_block)
        else:
            defn_str = defn_str.replace('$POETIC_BLOCK$', '')
        defn_strs.append(defn_str)
    html = html.replace('$DEFINITIONS$', '\n'.join(defn_strs))

    # Set up the endnote: word origin, synonyms, etc.
    endnote = entry_endnote_template
    endnote = endnote.replace('$ORIGIN$', entry['origin']);
    endnote = endnote.replace('$SYNONYMS$', ', '.join(entry['synonyms']));
    endnote = endnote.replace('$ANTONYMS$', ', '.join(entry['antonyms']));
    html = html.replace('$ENDNOTE$', endnote)

    with open(f'html/{word}.html', 'w') as f:
        f.write(html)


# ______________________________________________________________________
# Main

if __name__ == '__main__':

    # Load in the dictionary entries.
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

    # Load in the html template.
    with open('templates/definition_page_template.html') as f:
        html_template = f.read()

    # Make all the pages.
    for word in gpt_data:
        make_page_for_entry(word, gpt_data[word])
