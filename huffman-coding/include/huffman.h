#ifndef HUFFMAN_H
#define HUFFMAN_H

#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>

enum {
    HUFFMAN_OK = 0,
    HUFFMAN_ERROR_INVALID_ARGUMENT = -1,
    HUFFMAN_ERROR_EMPTY_INPUT = -2,
    HUFFMAN_ERROR_ALLOCATION = -3,
    HUFFMAN_ERROR_INVALID_BIT = -4,
    HUFFMAN_ERROR_TRUNCATED_BITSTREAM = -5,
    HUFFMAN_ERROR_INVALID_BITSTREAM = -6
};

typedef struct HuffmanTree HuffmanTree;

typedef struct {
    char *codes[256];
} HuffmanCodeTable;

int huffman_build(const unsigned char *input, size_t input_length, HuffmanTree **tree_out);
int huffman_generate_codes_top_down(const HuffmanTree *tree, HuffmanCodeTable *table);
int huffman_generate_codes_bottom_up(const HuffmanTree *tree, HuffmanCodeTable *table);
bool huffman_code_tables_equal(const HuffmanCodeTable *first, const HuffmanCodeTable *second);
int huffman_encode(const unsigned char *input, size_t input_length, const HuffmanCodeTable *table, char **bits_out);
int huffman_decode(const HuffmanTree *tree, const char *bits, unsigned char **output_out, size_t *output_length_out);
int huffman_export_dot(const HuffmanTree *tree, FILE *output);
int huffman_export_dot_selected(const HuffmanTree *tree, const bool selected_symbols[256], const HuffmanCodeTable *codes, FILE *output);
void huffman_code_table_free(HuffmanCodeTable *table);
void huffman_tree_free(HuffmanTree *tree);

#endif
