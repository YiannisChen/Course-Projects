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

    ASSERT_TRUE(huffman_build(NULL, 4, &tree) == HUFFMAN_ERROR_INVALID_ARGUMENT);
    ASSERT_TRUE(huffman_build(input, sizeof(input) - 1, &tree) == HUFFMAN_OK);
    ASSERT_TRUE(huffman_generate_codes_top_down(tree, &table) == HUFFMAN_OK);
    ASSERT_TRUE(huffman_encode(input, sizeof(input) - 1, &table, &bits) == HUFFMAN_OK);
    ASSERT_TRUE(table.codes[(unsigned char)'b'] != NULL);
    ASSERT_TRUE(strlen(table.codes[(unsigned char)'b']) > 1);
    truncated = malloc(strlen(table.codes[(unsigned char)'b']));
    ASSERT_TRUE(truncated != NULL);
    memcpy(truncated, table.codes[(unsigned char)'b'], strlen(table.codes[(unsigned char)'b']) - 1);
    truncated[strlen(table.codes[(unsigned char)'b']) - 1] = '\0';
    ASSERT_TRUE(huffman_decode(tree, "", &decoded, &decoded_length) == HUFFMAN_OK);
    ASSERT_TRUE(decoded_length == 0);
    free(decoded);
    decoded = NULL;
    ASSERT_TRUE(huffman_decode(tree, "0102", &decoded, &decoded_length) == HUFFMAN_ERROR_INVALID_BIT);
    ASSERT_TRUE(decoded == NULL);
    ASSERT_TRUE(huffman_decode(tree, truncated, &decoded, &decoded_length) == HUFFMAN_ERROR_TRUNCATED_BITSTREAM);
    ASSERT_TRUE(decoded == NULL);

    free(truncated);
    free(bits);
    huffman_code_table_free(&table);
    huffman_tree_free(tree);
    return 0;
}

static int test_high_byte_round_trip(void) {
    const unsigned char input[] = {0x00, 0x01, 0x7F, 0x80, 0xFE, 0xFF, 0x00, 0x80, 0xFF};
    return test_round_trip(input, sizeof(input));
}

static int test_all_256_symbols(void) {
    unsigned char input[256];
    for (size_t index = 0; index < 256; ++index) {
        input[index] = (unsigned char)index;
    }
    return test_round_trip(input, sizeof(input));
}

static int test_deterministic_equal_frequency_codes(void) {
    const unsigned char input[] = {'a', 'b', 'c', 'd'};
    HuffmanTree *reference_tree = NULL;
    HuffmanCodeTable reference = {0};

    ASSERT_TRUE(huffman_build(input, sizeof(input), &reference_tree) == HUFFMAN_OK);
    ASSERT_TRUE(huffman_generate_codes_bottom_up(reference_tree, &reference) == HUFFMAN_OK);
    ASSERT_TRUE(strcmp(reference.codes[(unsigned char)'a'], "00") == 0);
    ASSERT_TRUE(strcmp(reference.codes[(unsigned char)'b'], "01") == 0);
    ASSERT_TRUE(strcmp(reference.codes[(unsigned char)'c'], "10") == 0);
    ASSERT_TRUE(strcmp(reference.codes[(unsigned char)'d'], "11") == 0);
    huffman_tree_free(reference_tree);

    for (int attempt = 0; attempt < 8; ++attempt) {
        HuffmanTree *tree = NULL;
        HuffmanCodeTable bottom_up = {0};
        HuffmanCodeTable top_down = {0};
        ASSERT_TRUE(huffman_build(input, sizeof(input), &tree) == HUFFMAN_OK);
        ASSERT_TRUE(huffman_generate_codes_bottom_up(tree, &bottom_up) == HUFFMAN_OK);
        ASSERT_TRUE(huffman_generate_codes_top_down(tree, &top_down) == HUFFMAN_OK);
        ASSERT_TRUE(huffman_code_tables_equal(&reference, &bottom_up));
        ASSERT_TRUE(huffman_code_tables_equal(&bottom_up, &top_down));
        huffman_code_table_free(&bottom_up);
        huffman_code_table_free(&top_down);
        huffman_tree_free(tree);
    }

    huffman_code_table_free(&reference);
    return 0;
}

static int test_single_symbol_stream_validation(void) {
    const unsigned char input[] = {'x', 'x', 'x'};
    HuffmanTree *tree = NULL;
    HuffmanCodeTable table = {0};
    char *bits = NULL;
    unsigned char *decoded = NULL;
    size_t decoded_length = 0;

    ASSERT_TRUE(huffman_build(input, sizeof(input), &tree) == HUFFMAN_OK);
    ASSERT_TRUE(huffman_generate_codes_top_down(tree, &table) == HUFFMAN_OK);
    ASSERT_TRUE(strcmp(table.codes[(unsigned char)'x'], "0") == 0);
    ASSERT_TRUE(huffman_encode(input, sizeof(input), &table, &bits) == HUFFMAN_OK);
    ASSERT_TRUE(strcmp(bits, "000") == 0);
    ASSERT_TRUE(huffman_decode(tree, bits, &decoded, &decoded_length) == HUFFMAN_OK);
    ASSERT_TRUE(decoded_length == sizeof(input));
    ASSERT_TRUE(memcmp(decoded, input, sizeof(input)) == 0);
    free(decoded);
    decoded = NULL;
    ASSERT_TRUE(huffman_decode(tree, "", &decoded, &decoded_length) == HUFFMAN_OK);
    ASSERT_TRUE(decoded_length == 0);
    free(decoded);
    decoded = NULL;
    ASSERT_TRUE(huffman_decode(tree, "1", &decoded, &decoded_length) == HUFFMAN_ERROR_INVALID_BITSTREAM);
    ASSERT_TRUE(decoded == NULL);
    ASSERT_TRUE(huffman_decode(tree, "0a", &decoded, &decoded_length) == HUFFMAN_ERROR_INVALID_BIT);
    ASSERT_TRUE(decoded == NULL);

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

static int test_dot_export_includes_labeled_edges(void) {
    const unsigned char input[] = "abracadabra";
    HuffmanTree *tree = NULL;
    FILE *dot = tmpfile();
    char output[4096] = {0};
    ASSERT_TRUE(dot != NULL);
    ASSERT_TRUE(huffman_build(input, sizeof(input) - 1, &tree) == HUFFMAN_OK);
    ASSERT_TRUE(huffman_export_dot(tree, dot) == HUFFMAN_OK);
    rewind(dot);
    ASSERT_TRUE(fread(output, 1, sizeof(output) - 1, dot) > 0);
    ASSERT_TRUE(strstr(output, "digraph HuffmanTree") != NULL);
    ASSERT_TRUE(strstr(output, "label=\"0\"") != NULL);
    ASSERT_TRUE(strstr(output, "label=\"1\"") != NULL);
    fclose(dot);
    huffman_tree_free(tree);
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
    ASSERT_TRUE(test_high_byte_round_trip() == 0);
    ASSERT_TRUE(test_all_256_symbols() == 0);
    ASSERT_TRUE(test_deterministic_equal_frequency_codes() == 0);
    ASSERT_TRUE(test_single_symbol_stream_validation() == 0);
    ASSERT_TRUE(test_deterministic_randomized_round_trips() == 0);
    ASSERT_TRUE(test_dot_export_includes_labeled_edges() == 0);

    puts("Huffman tests passed");
    return 0;
}
