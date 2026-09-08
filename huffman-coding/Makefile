CC ?= cc
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Iinclude
SOURCES = src/huffman.c

.PHONY: all test sanitize clean

all: huffman

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
	rm -f huffman test-huffman test-huffman-sanitize
	rm -rf *.dSYM
