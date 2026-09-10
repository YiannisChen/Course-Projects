#include "huffman.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char *read_file(const char *path, size_t *length_out) {
    FILE *file = fopen(path, "rb");
    long length;
    unsigned char *buffer;

    if (file == NULL) return NULL;
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 0 || fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return NULL;
    }
    buffer = malloc((size_t)length + 1);
    if (buffer == NULL) {
        fclose(file);
        return NULL;
    }
    if (fread(buffer, 1, (size_t)length, file) != (size_t)length) {
        free(buffer);
        fclose(file);
        return NULL;
    }
    fclose(file);
    *length_out = (size_t)length;
    return buffer;
}

int main(int argc, char **argv) {
    static const unsigned char overview_symbols[] = {' ', 'e', 'a', 'r', 's', 'i', 't', 'o', 'n', 'h', 'c', 'd'};
    unsigned char *input;
    size_t input_length;
    HuffmanTree *tree = NULL;
    HuffmanCodeTable codes = {0};
    int result = 1;

    if (argc != 3 || (strcmp(argv[2], "full") != 0 && strcmp(argv[2], "overview") != 0)) {
        fprintf(stderr, "Usage: %s <input-file> <full|overview>\n", argv[0]);
        return 1;
    }
    input = read_file(argv[1], &input_length);
    if (input == NULL || input_length == 0) {
        fprintf(stderr, "Input file must be readable and non-empty.\n");
        free(input);
        return 1;
    }
    if (huffman_build(input, input_length, &tree) != HUFFMAN_OK) goto cleanup;
    if (strcmp(argv[2], "full") == 0) {
        if (huffman_export_dot(tree, stdout) != HUFFMAN_OK) goto cleanup;
    } else {
        bool selected[256] = {false};
        for (size_t index = 0; index < sizeof(overview_symbols); ++index) selected[overview_symbols[index]] = true;
        if (huffman_generate_codes_top_down(tree, &codes) != HUFFMAN_OK ||
            huffman_export_dot_selected(tree, selected, &codes, stdout) != HUFFMAN_OK) goto cleanup;
    }
    result = 0;
cleanup:
    free(input);
    huffman_code_table_free(&codes);
    huffman_tree_free(tree);
    return result;
}
