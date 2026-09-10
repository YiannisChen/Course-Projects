CC ?= cc
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Iinclude
SOURCES = src/huffman.c

.PHONY: all test sanitize clean

all: huffman

demo/trump-post-tree.svg: huffman-tree examples/trump.txt
	mkdir -p demo
	./huffman-tree examples/trump.txt full | dot -Tsvg -o $@

demo/trump-post-tree-overview.svg: huffman-tree examples/trump.txt
	mkdir -p demo
	./huffman-tree examples/trump.txt overview | dot -Tsvg -o $@

huffman-tree: src/export_tree.c $(SOURCES) include/huffman.h
	$(CC) $(CFLAGS) src/export_tree.c $(SOURCES) -o $@

huffman: src/main.c $(SOURCES) include/huffman.h
	$(CC) $(CFLAGS) src/main.c $(SOURCES) -o $@

test-huffman: tests/test_huffman.c $(SOURCES) include/huffman.h
	$(CC) $(CFLAGS) tests/test_huffman.c $(SOURCES) -o $@

test: huffman huffman-tree test-huffman
	./test-huffman
	sh tests/test_cli.sh

sanitize:
	$(CC) $(CFLAGS) -fsanitize=address,undefined -g tests/test_huffman.c $(SOURCES) -o test-huffman-sanitize
	./test-huffman-sanitize

clean:
	rm -f huffman huffman-tree test-huffman test-huffman-sanitize demo/trump-post-tree.svg demo/trump-post-tree-overview.svg
	rm -rf *.dSYM
