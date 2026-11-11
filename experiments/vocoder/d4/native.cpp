// Link-time adapter for the existing worker. Layout is generated from C5 evidence.
#include "opendmr.cpp"
#include "layout.hpp"
#include <algorithm>
#include <bitset>

extern "C" bool __wrap_opendmr_encode(opendmr_encoder_t* encoder, const int16_t* pcm,
                                        uint8_t* frame) {
    int params[9] = {};
    encoder->enc->encode_dmr_params(pcm, params);
    std::bitset<49> adapted;
    size_t offset = 0;
    for (int i = 0; i < 9; ++i) {
        for (int shift = widths[i]-1; shift >= 0; --shift)
            adapted.set(48-destinations[offset++], (params[i] >> shift) & 1);
    }
    uint64_t info = adapted.to_ullong();
    unsigned a = info >> 37;
    unsigned b = (info >> 25) & 4095;
    unsigned aword = CGolay24128::encode24128(a);
    unsigned bword = (CGolay24128::encode23127(b) >> 1) ^ compute_prng_mask_23bit(a);
    uint64_t tail = (uint64_t(bword) << 25) | (info & 0x1ffffff);
    for (unsigned i = 0; i < 3; ++i) frame[i] = aword >> (16-8*i);
    for (unsigned i = 0; i < 6; ++i) frame[3+i] = tail >> (40-8*i);
    return true;
}

extern "C" void __wrap_mbe_floattoshort(float* samples, short* pcm) {
    constexpr float limit = 32767.0f * 0.95f;
    for (int i = 0; i < 160; ++i)
        pcm[i] = static_cast<short>(std::max(-limit, std::min(limit, samples[i])));
}
