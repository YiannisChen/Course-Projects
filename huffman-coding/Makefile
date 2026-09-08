CC ?= cc
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Iinclude
SOURCES = src/huffman.c

.PHONY: all test sanitize clean

all: huffman

demo/tree.svg: src/export_demo.c $(SOURCES) include/huffman.h
	mkdir -p demo
	$(CC) $(CFLAGS) src/export_demo.c $(SOURCES) -o huffman-dot
	./huffman-dot > demo/tree.dot
	dot -Tsvg demo/tree.dot -o demo/tree.svg

huffman: src/main.c $(SOURCES) include/huffman.h
	$(CC) $(CFLAGS) src/main.c $(SOURCES) -o $@

test-huffman: tests/test_huffman.c $(SOURCES) include/huffman.h
	$(CC) $(CFLAGS) tests/test_huffman.c $(SOURCES) -o $@

test: huffman test-huffman
	./test-huffman
	sh tests/test_cli.sh

sanitize:
	$(CC) $(CFLAGS) -fsanitize=address,undefined -g tests/test_huffman.c $(SOURCES) -o test-huffman-sanitize
	./test-huffman-sanitize

clean:
	rm -f huffman huffman-dot test-huffman test-huffman-sanitize
	rm -rf *.dSYM
