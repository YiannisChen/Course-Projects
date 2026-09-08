#!/bin/sh
set -eu

output=$(./huffman examples/abracadabra.txt)
printf '%s\n' "$output" | grep -F 'Round-trip: PASS'
printf '%s\n' "$output" | grep -F 'Code-table equivalence: PASS'
