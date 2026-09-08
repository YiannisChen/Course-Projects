#include "huffman.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define HUFFMAN_MAX_NODES 511

typedef struct {
    size_t frequency;
    size_t order;
    int symbol;
    int parent;
    int left;
    int right;
} HuffmanNode;

struct HuffmanTree {
    HuffmanNode nodes[HUFFMAN_MAX_NODES];
    int leaf_indices[256];
    size_t node_count;
    int root;
};

static bool is_leaf(const HuffmanNode *node) {
    return node->left == -1 && node->right == -1;
}

static bool node_precedes(const HuffmanNode *first, const HuffmanNode *second) {
    return first->frequency < second->frequency ||
        (first->frequency == second->frequency && first->order < second->order);
}

static int select_minimum_unparented(const HuffmanTree *tree, int excluded) {
    int selected = -1;

    for (size_t index = 0; index < tree->node_count; ++index) {
        const HuffmanNode *node = &tree->nodes[index];
        if (node->parent != -1 || (int)index == excluded) {
            continue;
        }
        if (selected == -1 || node_precedes(node, &tree->nodes[selected])) {
            selected = (int)index;
        }
    }
    return selected;
}

static int copy_code(HuffmanCodeTable *table, unsigned char symbol, const char *code, size_t length) {
    char *copy = malloc(length + 1);
    if (copy == NULL) {
        return HUFFMAN_ERROR_ALLOCATION;
    }
    memcpy(copy, code, length);
    copy[length] = '\0';
    table->codes[symbol] = copy;
    return HUFFMAN_OK;
}

static int generate_codes_top_down_from_node(
    const HuffmanTree *tree,
    int node_index,
    char *path,
    size_t path_length,
    HuffmanCodeTable *table
) {
    const HuffmanNode *node = &tree->nodes[node_index];
    if (is_leaf(node)) {
        if (path_length == 0) {
            path[0] = '0';
            return copy_code(table, (unsigned char)node->symbol, path, 1);
        }
        return copy_code(table, (unsigned char)node->symbol, path, path_length);
    }

    path[path_length] = '0';
    int result = generate_codes_top_down_from_node(tree, node->left, path, path_length + 1, table);
    if (result != HUFFMAN_OK) {
        return result;
    }
    path[path_length] = '1';
    return generate_codes_top_down_from_node(tree, node->right, path, path_length + 1, table);
}

void huffman_code_table_free(HuffmanCodeTable *table) {
    if (table == NULL) {
        return;
    }
    for (size_t symbol = 0; symbol < 256; ++symbol) {
        free(table->codes[symbol]);
        table->codes[symbol] = NULL;
    }
}

void huffman_tree_free(HuffmanTree *tree) {
    free(tree);
}

int huffman_build(const unsigned char *input, size_t input_length, HuffmanTree **tree_out) {
    size_t frequencies[256] = {0};
    HuffmanTree *tree = NULL;

    if (tree_out == NULL || (input == NULL && input_length != 0)) {
        return HUFFMAN_ERROR_INVALID_ARGUMENT;
    }
    *tree_out = NULL;
    if (input_length == 0) {
        return HUFFMAN_ERROR_EMPTY_INPUT;
    }
    for (size_t index = 0; index < input_length; ++index) {
        if (frequencies[input[index]] == SIZE_MAX) {
            return HUFFMAN_ERROR_ALLOCATION;
        }
        ++frequencies[input[index]];
    }

    tree = calloc(1, sizeof(*tree));
    if (tree == NULL) {
        return HUFFMAN_ERROR_ALLOCATION;
    }
    for (size_t symbol = 0; symbol < 256; ++symbol) {
        tree->leaf_indices[symbol] = -1;
        if (frequencies[symbol] == 0) {
            continue;
        }
        HuffmanNode *node = &tree->nodes[tree->node_count];
        node->frequency = frequencies[symbol];
        node->order = tree->node_count;
        node->symbol = (int)symbol;
        node->parent = -1;
        node->left = -1;
        node->right = -1;
        tree->leaf_indices[symbol] = (int)tree->node_count;
        ++tree->node_count;
    }

    while (tree->node_count > 1) {
        int first = select_minimum_unparented(tree, -1);
        int second = select_minimum_unparented(tree, first);
        if (second == -1) {
            break;
        }
        if (tree->node_count >= HUFFMAN_MAX_NODES) {
            free(tree);
            return HUFFMAN_ERROR_ALLOCATION;
        }
        HuffmanNode *parent = &tree->nodes[tree->node_count];
        parent->frequency = tree->nodes[first].frequency + tree->nodes[second].frequency;
        parent->order = tree->node_count;
        parent->symbol = -1;
        parent->parent = -1;
        parent->left = first;
        parent->right = second;
        tree->nodes[first].parent = (int)tree->node_count;
        tree->nodes[second].parent = (int)tree->node_count;
        ++tree->node_count;
    }

    tree->root = select_minimum_unparented(tree, -1);
    if (tree->root == -1) {
        free(tree);
        return HUFFMAN_ERROR_INVALID_BITSTREAM;
    }
    *tree_out = tree;
    return HUFFMAN_OK;
}

int huffman_generate_codes_top_down(const HuffmanTree *tree, HuffmanCodeTable *table) {
    char path[256] = {0};
    if (tree == NULL || table == NULL) {
        return HUFFMAN_ERROR_INVALID_ARGUMENT;
    }
    huffman_code_table_free(table);
    return generate_codes_top_down_from_node(tree, tree->root, path, 0, table);
}

int huffman_generate_codes_bottom_up(const HuffmanTree *tree, HuffmanCodeTable *table) {
    if (tree == NULL || table == NULL) {
        return HUFFMAN_ERROR_INVALID_ARGUMENT;
    }
    huffman_code_table_free(table);
    for (size_t symbol = 0; symbol < 256; ++symbol) {
        int node_index = tree->leaf_indices[symbol];
        char reverse_path[256];
        size_t length = 0;
        if (node_index == -1) {
            continue;
        }
        while (tree->nodes[node_index].parent != -1) {
            int parent_index = tree->nodes[node_index].parent;
            reverse_path[length++] = tree->nodes[parent_index].left == node_index ? '0' : '1';
            node_index = parent_index;
        }
        if (length == 0) {
            reverse_path[length++] = '0';
        }
        for (size_t index = 0; index < length / 2; ++index) {
            char temporary = reverse_path[index];
            reverse_path[index] = reverse_path[length - 1 - index];
            reverse_path[length - 1 - index] = temporary;
        }
        int result = copy_code(table, (unsigned char)symbol, reverse_path, length);
        if (result != HUFFMAN_OK) {
            huffman_code_table_free(table);
            return result;
        }
    }
    return HUFFMAN_OK;
}

bool huffman_code_tables_equal(const HuffmanCodeTable *first, const HuffmanCodeTable *second) {
    if (first == NULL || second == NULL) {
        return false;
    }
    for (size_t symbol = 0; symbol < 256; ++symbol) {
        if (first->codes[symbol] == NULL || second->codes[symbol] == NULL) {
            if (first->codes[symbol] != second->codes[symbol]) {
                return false;
            }
            continue;
        }
        if (strcmp(first->codes[symbol], second->codes[symbol]) != 0) {
            return false;
        }
    }
    return true;
}

int huffman_encode(const unsigned char *input, size_t input_length, const HuffmanCodeTable *table, char **bits_out) {
    size_t bit_length = 0;
    char *bits = NULL;
    size_t cursor = 0;

    if (table == NULL || bits_out == NULL || (input == NULL && input_length != 0)) {
        return HUFFMAN_ERROR_INVALID_ARGUMENT;
    }
    *bits_out = NULL;
    for (size_t index = 0; index < input_length; ++index) {
        size_t code_length;
        if (table->codes[input[index]] == NULL) {
            return HUFFMAN_ERROR_INVALID_ARGUMENT;
        }
        code_length = strlen(table->codes[input[index]]);
        if (code_length > SIZE_MAX - bit_length - 1) {
            return HUFFMAN_ERROR_ALLOCATION;
        }
        bit_length += code_length;
    }
    bits = malloc(bit_length + 1);
    if (bits == NULL) {
        return HUFFMAN_ERROR_ALLOCATION;
    }
    for (size_t index = 0; index < input_length; ++index) {
        size_t code_length = strlen(table->codes[input[index]]);
        memcpy(bits + cursor, table->codes[input[index]], code_length);
        cursor += code_length;
    }
    bits[cursor] = '\0';
    *bits_out = bits;
    return HUFFMAN_OK;
}

int huffman_decode(const HuffmanTree *tree, const char *bits, unsigned char **output_out, size_t *output_length_out) {
    size_t bit_length;
    unsigned char *output;
    size_t output_length = 0;
    int node_index;

    if (tree == NULL || bits == NULL || output_out == NULL || output_length_out == NULL) {
        return HUFFMAN_ERROR_INVALID_ARGUMENT;
    }
    *output_out = NULL;
    *output_length_out = 0;
    bit_length = strlen(bits);
    output = malloc(bit_length + 1);
    if (output == NULL) {
        return HUFFMAN_ERROR_ALLOCATION;
    }
    if (is_leaf(&tree->nodes[tree->root])) {
        for (size_t index = 0; index < bit_length; ++index) {
            if (bits[index] != '0') {
                free(output);
                return bits[index] == '1' ? HUFFMAN_ERROR_INVALID_BITSTREAM : HUFFMAN_ERROR_INVALID_BIT;
            }
            output[output_length++] = (unsigned char)tree->nodes[tree->root].symbol;
        }
        *output_out = output;
        *output_length_out = output_length;
        return HUFFMAN_OK;
    }

    node_index = tree->root;
    for (size_t index = 0; index < bit_length; ++index) {
        if (bits[index] == '0') {
            node_index = tree->nodes[node_index].left;
        } else if (bits[index] == '1') {
            node_index = tree->nodes[node_index].right;
        } else {
            free(output);
            return HUFFMAN_ERROR_INVALID_BIT;
        }
        if (node_index < 0) {
            free(output);
            return HUFFMAN_ERROR_INVALID_BITSTREAM;
        }
        if (is_leaf(&tree->nodes[node_index])) {
            output[output_length++] = (unsigned char)tree->nodes[node_index].symbol;
            node_index = tree->root;
        }
    }
    if (node_index != tree->root) {
        free(output);
        return HUFFMAN_ERROR_TRUNCATED_BITSTREAM;
    }
    *output_out = output;
    *output_length_out = output_length;
    return HUFFMAN_OK;
}
