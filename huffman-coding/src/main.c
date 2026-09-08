#include "huffman.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char *read_file(const char *path, size_t *length_out) {
    FILE *file = fopen(path, "rb");
    long length;
    unsigned char *buffer;
    if (file == NULL) return NULL;
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 0 || fseek(file, 0, SEEK_SET) != 0) { fclose(file); return NULL; }
    buffer = malloc((size_t)length + 1);
    if (buffer == NULL) { fclose(file); return NULL; }
    if (fread(buffer, 1, (size_t)length, file) != (size_t)length) { free(buffer); fclose(file); return NULL; }
    fclose(file);
    *length_out = (size_t)length;
    return buffer;
}

int main(int argc, char **argv) {
    unsigned char *input, *decoded = NULL;
    size_t input_length, decoded_length = 0, frequencies[256] = {0};
    HuffmanTree *tree = NULL;
    HuffmanCodeTable top_down = {0}, bottom_up = {0};
    char *bits = NULL;
    int result = 1;
    if (argc != 2) { fprintf(stderr, "Usage: %s <input-file>\n", argv[0]); return 1; }
    input = read_file(argv[1], &input_length);
    if (input == NULL || input_length == 0) { fprintf(stderr, "Input file must be readable and non-empty.\n"); free(input); return 1; }
    for (size_t i = 0; i < input_length; ++i) ++frequencies[input[i]];
    if (huffman_build(input, input_length, &tree) != HUFFMAN_OK ||
        huffman_generate_codes_top_down(tree, &top_down) != HUFFMAN_OK ||
        huffman_generate_codes_bottom_up(tree, &bottom_up) != HUFFMAN_OK ||
        huffman_encode(input, input_length, &top_down, &bits) != HUFFMAN_OK ||
        huffman_decode(tree, bits, &decoded, &decoded_length) != HUFFMAN_OK) goto cleanup;
    printf("Input (%zu bytes):\n", input_length); fwrite(input, 1, input_length, stdout); puts("\nFrequency and code tables:");
    for (size_t symbol = 0; symbol < 256; ++symbol) if (frequencies[symbol] != 0)
        printf("0x%02zx  frequency=%zu  top-down=%s  bottom-up=%s\n", symbol, frequencies[symbol], top_down.codes[symbol], bottom_up.codes[symbol]);
    printf("Encoded bits: %s\nDecoded text:\n", bits); fwrite(decoded, 1, decoded_length, stdout); putchar('\n');
    printf("Round-trip: %s\n", decoded_length == input_length && memcmp(decoded, input, input_length) == 0 ? "PASS" : "FAIL");
    printf("Code-table equivalence: %s\n", huffman_code_tables_equal(&top_down, &bottom_up) ? "PASS" : "FAIL");
    result = 0;
cleanup:
    free(input); free(bits); free(decoded); huffman_code_table_free(&top_down); huffman_code_table_free(&bottom_up); huffman_tree_free(tree);
    return result;
}
