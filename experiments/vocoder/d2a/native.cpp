// Reuse the exact post-parameter packing entry point exercised in C5/C7.
#define main unused_c5_entry
#include "/c5/pack.cpp"
#undef main

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    emit(Bits(argv[1]));
    std::string hex(argv[2]);
    if (hex.size() != 18) return 3;
    uint8_t bytes[9];
    for (size_t i = 0; i < 9; ++i)
        bytes[i] = std::stoul(hex.substr(2*i, 2), nullptr, 16);
    char recovered[49];
    decode_ambe_frame(bytes, recovered);
    std::putchar(' ');
    for (char bit : recovered) std::printf("%d", int(bit));
    std::putchar('\n');
}
