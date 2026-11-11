#define main unused_c5_entry
#include "/bank/c5/pack.cpp"
#undef main

int main() {
    uint8_t frame[9];
    while (std::fread(frame, sizeof(frame), 1, stdin) == 1) {
        char recovered[49];
        decode_ambe_frame(frame, recovered);
        std::string info;
        for (char bit : recovered) info.push_back('0' + bit);
        std::cout << info;
        emit(Bits(info));
        std::cout << '\n';
    }
    return std::ferror(stdin) ? 1 : 0;
}
