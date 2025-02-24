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
from collections import defaultdict


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

entry_endnote_template = '''
        <div class="origin-synonyms">
            <div class="end-div">
                <div class="label">ORIGIN</div>
                $ORIGIN$
            </div>
            $SYNONYMS$
            $ANTONYMS$
        </div>
'''

endnote_section_template = '''
            <div class="end-div">
                <div class="label">$TITLE$</div>
                $CONTENT$
            </div>
'''

def make_endnote_section(title, content_list):
    ''' This returns the empty string if content_list is an empty list;
        otherwise it returns endnote_section_template with the $TITLE$
        and $CONTENT$ fields filled in based on the arguments. '''
    if len(content_list) == 0:
        return ''
    section = endnote_section_template
    section = section.replace('$TITLE$', title)
    section = section.replace('$CONTENT$', ', '.join(content_list))
    return section

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
    syn_section = make_endnote_section('SYNONYMS', entry['synonyms']);
    endnote = endnote.replace('$SYNONYMS$', syn_section);
    ant_section = make_endnote_section('ANTONYMS', entry['antonyms']);
    endnote = endnote.replace('$ANTONYMS$', ant_section);
    html = html.replace('$ENDNOTE$', endnote)

    with open(f'html/{word}.html', 'w') as f:
        f.write(html)

def make_index_page(words):
    ''' Given a list of words, generate the HTML content for the word index and save it
        disk in the html/ directory.

        The words are sorted and grouped under their starting letter.
    '''

    # Load the template.
    with open('templates/index_page_template.html') as f:
        html = f.read()

    # Sort words and categorize them by their starting letter.
    words_by_letter = defaultdict(list)
    for word in sorted(words, key=str.lower):
        first_letter = word[0].lower()
        words_by_letter[first_letter].append(word)

    # Create the HTML sections for each letter.
    index_html = []
    ind = ' ' * 8  # Indent.
    for letter in sorted(words_by_letter.keys()):
        index_html.append(ind + f'<div class="letter-section">')
        index_html.append(ind + f'  <div class="letter">{letter}</div>')
        index_html.append(ind +  '  <div class="word-list">')
        for word in words_by_letter[letter]:
            index_html.append(ind + f'    <a href="{word}.html">{word}</a>')
        index_html.append(ind + '  </div>')
        index_html.append(ind + '</div>')
    html = html.replace('$WORD_INDEX$', '\n'.join(index_html))

    # Save the index html to disk.
    with open('html/word_index.html', 'w') as f:
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

    # Make the index page.
    make_index_page(list(gpt_data))
