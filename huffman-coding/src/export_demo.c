#include "huffman.h"
#include <stdio.h>

int main(void) {
    const unsigned char input[] = "abracadabra";
    HuffmanTree *tree = NULL;
    int result = huffman_build(input, sizeof(input) - 1, &tree);
    if (result == HUFFMAN_OK) result = huffman_export_dot(tree, stdout);
    huffman_tree_free(tree);
    return result == HUFFMAN_OK ? 0 : 1;
}
