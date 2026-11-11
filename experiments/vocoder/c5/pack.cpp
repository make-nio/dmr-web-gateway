#include <array>
#include <bitset>
#include <cstdio>
#include <fstream>
#include <iostream>
#include "opendmr.cpp"

using Bits = std::bitset<49>;
constexpr int widths[] = {7, 5, 5, 9, 7, 5, 4, 4, 3};

void emit(const Bits& bits) {
    uint64_t info = bits.to_ullong();
    unsigned a = info >> 37;
    unsigned b = (info >> 25) & 4095;
    unsigned aword = CGolay24128::encode24128(a);
    unsigned bword = (CGolay24128::encode23127(b) >> 1) ^ compute_prng_mask_23bit(a);
    uint64_t tail = (uint64_t(bword) << 25) | (info & 0x1ffffff);
    uint8_t frame[9];
    for (int i = 0; i < 3; ++i) frame[i] = aword >> (16-8*i);
    for (int i = 0; i < 6; ++i) frame[3+i] = tail >> (40-8*i);
    char recovered[49];
    decode_ambe_frame(frame, recovered);
    std::printf(" ");
    for (uint8_t byte : frame) std::printf("%02x", unsigned(byte));
    std::printf(" ");
    for (char bit : recovered) std::printf("%d", int(bit));
}

int main() {
    std::ifstream layout("/tmp/layout");
    std::array<int, 49> dest;
    Bits used;
    for (int& pos : dest) {
        if (!(layout >> pos) || pos < 0 || pos >= 49 || used.test(pos)) return 1;
        used.set(pos);
    }
    auto enc = opendmr_encoder_create();
    if (!enc) return 2;
    int16_t pcm[160];
    while (std::fread(pcm, sizeof(pcm), 1, stdin) == 1) {
        int params[9] = {};
        enc->enc->encode_dmr_params(pcm, params);
        Bits contiguous, adapted;
        int k = 0;
        for (int i = 0; i < 9; ++i) {
            if (params[i] < 0 || params[i] >= (1 << widths[i])) return 3;
            std::cout << params[i] << ' ';
            for (int shift = widths[i]-1; shift >= 0; --shift, ++k) {
                bool bit = (params[i] >> shift) & 1;
                contiguous.set(48-k, bit);
                adapted.set(48-dest[k], bit);
            }
        }
        std::cout << contiguous << ' ' << adapted;
        emit(contiguous);
        emit(adapted);
        std::cout << '\n';
    }
    opendmr_encoder_destroy(enc);
    return std::ferror(stdin) ? 4 : 0;
}
