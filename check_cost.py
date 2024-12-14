#!/usr/bin/env python3
# coding: utf-8
''' check_cost.py

    This script summarizes money spent on building dictionary entries.

    Usage:

        ./check_cost all       # Prints out the total money spent.
        ./check_cost latest    # Prints out the most recent money spent.

    This uses the cost reports in the file entries.json.

    It also uses the hidden file .latest_lines.txt to store the number of lines
    already seen in entries.json.
'''


# ______________________________________________________________________
# Imports

import json
import sys
from pathlib import Path


# ______________________________________________________________________
# Main

if __name__ == '__main__':

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    assert sys.argv[1] in ['latest', 'all']

    start_line = 0

    latest_file = Path('.latest.txt')
    if sys.argv[1] == 'latest' and latest_file.exists():
        with latest_file.open() as f:
            start_line = int(f.read())

    cost = 0
    num_entries = 0
    with open('entries.json') as f:
        for i, line in enumerate(f):
            if i < start_line:
                continue
            entry = json.loads(line)
            cost += entry['cost']
            num_entries += 1
    with latest_file.open('w') as f:
        f.write(f'{i + 1}\n')

    print(f'Cost: ${cost:.2f}')
    avg_per_thousand = cost / num_entries * 1_000
    print(f'Average per thousand entries: ${avg_per_thousand:.2f}')
