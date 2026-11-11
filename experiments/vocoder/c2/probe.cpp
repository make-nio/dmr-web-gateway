#include <cstdio>
#include "opendmr.cpp"

int main() {
    auto encoder = opendmr_encoder_create();
    if (!encoder) return 1;
    for (int index = 0; index < 4; ++index) {
        int16_t samples[160];
        if (std::fread(samples, sizeof(samples), 1, stdin) != 1) return 2;
        int params[9] = {};
        encoder->enc->encode_dmr_params(samples, params);
        uint8_t frame[9];
        encode_ambe_frame(params, frame);
        char recovered[49];
        decode_ambe_frame(frame, recovered);
        for (int value : params) std::printf("%d ", value);
        for (uint8_t byte : frame) std::printf("%02x", byte);
        std::putchar(' ');
        for (char bit : recovered) std::printf("%d", int(bit));
        std::putchar('\n');
    }
    opendmr_encoder_destroy(encoder);
}
