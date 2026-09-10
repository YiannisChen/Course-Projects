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
    int result = generate_codes_top_down_from_node(tree, tree->root, path, 0, table);
    if (result != HUFFMAN_OK) {
        huffman_code_table_free(table);
    }
    return result;
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

static void export_graph_header(FILE *output, const char *rankdir) {
    fprintf(output, "digraph HuffmanTree {\n  graph [rankdir=%s,nodesep=0.35,ranksep=0.5,pad=0.15,bgcolor=white,splines=polyline];\n  node [fontname=Helvetica,fontsize=10,color=\"#64748B\",penwidth=0.8];\n  edge [fontname=Helvetica,fontsize=9,color=\"#64748B\",penwidth=0.8];\n", rankdir);
}

static void export_leaf_node(FILE *output, size_t index, const HuffmanNode *node, const char *code) {
    unsigned char symbol = (unsigned char)node->symbol;
    char label[8];

    if (symbol == ' ') {
        strcpy(label, "space");
    } else if (symbol >= 32 && symbol <= 126) {
        if (symbol == '\\' || symbol == '\"') {
            label[0] = '\\';
            label[1] = (char)symbol;
            label[2] = '\0';
        } else {
            label[0] = (char)symbol;
            label[1] = '\0';
        }
    } else {
        snprintf(label, sizeof(label), "0x%02X", symbol);
    }
    if (code == NULL) {
        fprintf(output, "  n%zu [shape=box,style=\"rounded,filled\",fillcolor=\"#EFF6FF\",label=\"%s\\n%zu\"];\n", index, label, node->frequency);
    } else {
        fprintf(output, "  n%zu [shape=box,style=\"rounded,filled\",fillcolor=\"#EFF6FF\",label=\"%s\\n%zu · %s\"];\n", index, label, node->frequency, code);
    }
}

int huffman_export_dot(const HuffmanTree *tree, FILE *output) {
    if (tree == NULL || output == NULL) return HUFFMAN_ERROR_INVALID_ARGUMENT;
    export_graph_header(output, "LR");
    for (size_t index = 0; index < tree->node_count; ++index) {
        const HuffmanNode *node = &tree->nodes[index];
        if (is_leaf(node)) {
            export_leaf_node(output, index, node, NULL);
        } else {
            fprintf(output, "  n%zu [shape=ellipse,style=filled,fillcolor=\"#F1F5F9\",label=\"%zu\"];\n", index, node->frequency);
            fprintf(output, "  n%zu -> n%d [label=\"0\"];\n  n%zu -> n%d [label=\"1\"];\n", index, node->left, index, node->right);
        }
    }
    return fputs("}\n", output) == EOF ? HUFFMAN_ERROR_INVALID_ARGUMENT : HUFFMAN_OK;
}

static bool mark_selected_nodes(const HuffmanTree *tree, int node_index, const bool selected_symbols[256], bool included[HUFFMAN_MAX_NODES]) {
    const HuffmanNode *node = &tree->nodes[node_index];
    if (is_leaf(node)) {
        included[node_index] = selected_symbols[(unsigned char)node->symbol];
        return included[node_index];
    }
    bool includes_left = mark_selected_nodes(tree, node->left, selected_symbols, included);
    bool includes_right = mark_selected_nodes(tree, node->right, selected_symbols, included);
    included[node_index] = includes_left || includes_right;
    return included[node_index];
}

int huffman_export_dot_selected(const HuffmanTree *tree, const bool selected_symbols[256], const HuffmanCodeTable *codes, FILE *output) {
    bool included[HUFFMAN_MAX_NODES] = {false};

    if (tree == NULL || selected_symbols == NULL || codes == NULL || output == NULL) return HUFFMAN_ERROR_INVALID_ARGUMENT;
    if (!mark_selected_nodes(tree, tree->root, selected_symbols, included)) return HUFFMAN_ERROR_INVALID_ARGUMENT;
    export_graph_header(output, "TB");
    fprintf(output, "  labelloc=\"t\";\n  label=\"Selected paths from the generated Huffman tree\";\n  fontname=Helvetica;\n  fontsize=14;\n");
    for (size_t index = 0; index < tree->node_count; ++index) {
        const HuffmanNode *node = &tree->nodes[index];
        if (!included[index]) continue;
        if (is_leaf(node)) {
            const char *code = codes->codes[(unsigned char)node->symbol];
            if (code == NULL) return HUFFMAN_ERROR_INVALID_ARGUMENT;
            export_leaf_node(output, index, node, code);
        } else {
            if ((int)index == tree->root)
                fprintf(output, "  n%zu [shape=doublecircle,style=filled,fillcolor=\"#E2E8F0\",penwidth=1.2,label=\"%zu\"];\n", index, node->frequency);
            else
                fprintf(output, "  n%zu [shape=ellipse,style=filled,fillcolor=\"#F1F5F9\",label=\"%zu\"];\n", index, node->frequency);
            if (included[node->left]) fprintf(output, "  n%zu -> n%d [label=\"0\"];\n", index, node->left);
            if (included[node->right]) fprintf(output, "  n%zu -> n%d [label=\"1\"];\n", index, node->right);
        }
    }
    return fputs("}\n", output) == EOF ? HUFFMAN_ERROR_INVALID_ARGUMENT : HUFFMAN_OK;
}
