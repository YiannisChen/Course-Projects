#!/bin/sh
set -eu

output=$(./huffman examples/trump.txt)
printf '%s\n' "$output" | grep -F 'Round-trip: PASS'
printf '%s\n' "$output" | grep -F 'Code-table equivalence: PASS'
printf '%s\n' "$output" | grep -F 'Original size:              284 bytes / 2272 bits'
printf '%s\n' "$(./huffman-tree examples/trump.txt full)" | grep -F 'label="284"'
printf '%s\n' "$(./huffman-tree examples/trump.txt overview)" | grep -F 'Selected paths from the generated Huffman tree'
