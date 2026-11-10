#include <algorithm>
#include <array>
#include <bitset>
#include <cstdio>
#include <iostream>
#include <string>
#include "opendmr.cpp"

using Params = std::array<int, 9>;
using Frame = std::array<uint8_t, 9>;
constexpr int widths[] = {7, 5, 5, 9, 7, 5, 4, 4, 3};

void emitPair(const Params& params) {
    uint64_t info = 0;
    for (size_t i = 0; i < params.size(); ++i)
        info = (info << widths[i]) | params[i];
    unsigned a = info >> 37;
    unsigned b = (info >> 25) & 4095U;
    Frame control;
    encode_ambe_frame(params.data(), control.data());
    Frame variant = control;
    unsigned word = (CGolay24128::encode23127(b) >> 1) ^ compute_prng_mask_23bit(a);
    for (unsigned i = 0; i < 23; ++i) {
        unsigned pos = 24 + i;
        unsigned mask = 1U << (7 - pos % 8);
        if ((word >> (22 - i)) & 1U) variant[pos / 8] |= mask;
        else variant[pos / 8] &= ~mask;
    }
    std::cout << std::bitset<49>(info);
    for (const Frame* frame : {&control, &variant}) {
        char recovered[49];
        decode_ambe_frame(frame->data(), recovered);
        std::printf(" ");
        for (auto byte : *frame) std::printf("%02x", unsigned(byte));
        std::printf(" ");
        for (char bit : recovered) std::printf("%d", int(bit));
    }
    std::printf("\n");
}

int main(int argc, char** argv) {
    if (argc != 2) return 1;
    if (std::string(argv[1]) == "sweep") {
        for (unsigned b = 0; b < 4096; ++b) {
            unsigned a = (17*b + 53) & 4095;
            unsigned c = (b*8191 + 7) & 0x1ffffff;
            uint64_t info = (uint64_t(a) << 37) | (uint64_t(b) << 25) | c;
            Params p{};
            for (int i = 8; i >= 0; --i) {
                p[i] = info & ((1U << widths[i]) - 1);
                info >>= widths[i];
            }
            emitPair(p);
        }
        return 0;
    }
    if (std::string(argv[1]) != "speech") return 1;
    auto enc = opendmr_encoder_create();
    if (!enc) return 2;
    int16_t samples[160];
    while (std::fread(samples, sizeof(samples), 1, stdin) == 1) {
        Params params{};
        enc->enc->encode_dmr_params(samples, params.data());
        emitPair(params);
    }
    opendmr_encoder_destroy(enc);
    return 0;
}
