#include "huffman.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ASSERT_TRUE(condition) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "Assertion failed at %s:%d: %s\n", __FILE__, __LINE__, #condition); \
            return 1; \
        } \
    } while (0)

static int test_round_trip(const unsigned char *input, size_t input_length) {
    HuffmanTree *tree = NULL;
    HuffmanCodeTable top_down = {0};
    HuffmanCodeTable bottom_up = {0};
    char *bits = NULL;
    unsigned char *decoded = NULL;
    size_t decoded_length = 0;

    ASSERT_TRUE(huffman_build(input, input_length, &tree) == HUFFMAN_OK);
    ASSERT_TRUE(huffman_generate_codes_top_down(tree, &top_down) == HUFFMAN_OK);
    ASSERT_TRUE(huffman_generate_codes_bottom_up(tree, &bottom_up) == HUFFMAN_OK);
    ASSERT_TRUE(huffman_code_tables_equal(&top_down, &bottom_up));
    ASSERT_TRUE(huffman_encode(input, input_length, &top_down, &bits) == HUFFMAN_OK);
    ASSERT_TRUE(huffman_decode(tree, bits, &decoded, &decoded_length) == HUFFMAN_OK);
    ASSERT_TRUE(decoded_length == input_length);
    ASSERT_TRUE(memcmp(decoded, input, input_length) == 0);

    free(bits);
    free(decoded);
    huffman_code_table_free(&top_down);
    huffman_code_table_free(&bottom_up);
    huffman_tree_free(tree);
    return 0;
}

static int test_empty_input(void) {
    HuffmanTree *tree = NULL;
    ASSERT_TRUE(huffman_build((const unsigned char *)"", 0, &tree) == HUFFMAN_ERROR_EMPTY_INPUT);
    ASSERT_TRUE(tree == NULL);
    return 0;
}

static int test_invalid_and_truncated_bitstreams(void) {
    const unsigned char input[] = "abracadabra";
    HuffmanTree *tree = NULL;
    HuffmanCodeTable table = {0};
    char *bits = NULL;
    char *truncated = NULL;
    unsigned char *decoded = NULL;
    size_t decoded_length = 0;

    ASSERT_TRUE(huffman_build(input, sizeof(input) - 1, &tree) == HUFFMAN_OK);
    ASSERT_TRUE(huffman_generate_codes_top_down(tree, &table) == HUFFMAN_OK);
    ASSERT_TRUE(huffman_encode(input, sizeof(input) - 1, &table, &bits) == HUFFMAN_OK);
    ASSERT_TRUE(table.codes[(unsigned char)'b'] != NULL);
    ASSERT_TRUE(strlen(table.codes[(unsigned char)'b']) > 1);
    truncated = malloc(strlen(table.codes[(unsigned char)'b']));
    ASSERT_TRUE(truncated != NULL);
    memcpy(truncated, table.codes[(unsigned char)'b'], strlen(table.codes[(unsigned char)'b']) - 1);
    truncated[strlen(table.codes[(unsigned char)'b']) - 1] = '\0';
    ASSERT_TRUE(huffman_decode(tree, "0102", &decoded, &decoded_length) == HUFFMAN_ERROR_INVALID_BIT);
    ASSERT_TRUE(huffman_decode(tree, truncated, &decoded, &decoded_length) == HUFFMAN_ERROR_TRUNCATED_BITSTREAM);

    free(truncated);
    free(bits);
    huffman_code_table_free(&table);
    huffman_tree_free(tree);
    return 0;
}

static int test_deterministic_randomized_round_trips(void) {
    unsigned char input[128];
    unsigned int state = 0xC0FFEEu;

    for (size_t sample = 0; sample < 100; ++sample) {
        size_t length = 1 + (sample % sizeof(input));
        for (size_t index = 0; index < length; ++index) {
            state = state * 1664525u + 1013904223u;
            input[index] = (unsigned char)(state >> 24);
        }
        ASSERT_TRUE(test_round_trip(input, length) == 0);
    }
    return 0;
}

int main(void) {
    const unsigned char abracadabra[] = "abracadabra";
    const unsigned char hello[] = "hello world";
    const unsigned char repeated[] = "aaaaaaaa";
    const unsigned char single[] = "x";
    const unsigned char mixed[] = "Hello, World! 2026";
    const unsigned char newline[] = "first line\nsecond line\n";
    const unsigned char punctuation[] = "[]{}()!?;:,.+-=*/\\\\|~`0123456789";

    ASSERT_TRUE(test_round_trip(abracadabra, sizeof(abracadabra) - 1) == 0);
    ASSERT_TRUE(test_round_trip(hello, sizeof(hello) - 1) == 0);
    ASSERT_TRUE(test_round_trip(repeated, sizeof(repeated) - 1) == 0);
    ASSERT_TRUE(test_round_trip(single, sizeof(single) - 1) == 0);
    ASSERT_TRUE(test_round_trip(mixed, sizeof(mixed) - 1) == 0);
    ASSERT_TRUE(test_round_trip(newline, sizeof(newline) - 1) == 0);
    ASSERT_TRUE(test_round_trip(punctuation, sizeof(punctuation) - 1) == 0);
    ASSERT_TRUE(test_empty_input() == 0);
    ASSERT_TRUE(test_invalid_and_truncated_bitstreams() == 0);
    ASSERT_TRUE(test_deterministic_randomized_round_trips() == 0);

    puts("Huffman tests passed");
    return 0;
}
