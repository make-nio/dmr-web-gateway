#include <array>
#include <bitset>
#include <iostream>
#include <set>
#include <string>
#include "opendmr.cpp"

using Golay = CGolay24128;
constexpr unsigned low23 = (1U << 23) - 1;

// All arguments to decode23127 are within its 23-bit domain.
int main() {
    std::set<unsigned> distinct;
    unsigned aligned = 0, canonicalOK = 0, nativeOK = 0, highBit = 0;
    for (unsigned input = 0; input < 4096; ++input) {
        unsigned raw = Golay::encode23127(input);
        unsigned canonical = Golay::encode24128(input) >> 1;
        aligned += raw == (canonical << 1);
        canonicalOK += Golay::decode23127(canonical) == input;
        highBit += raw > low23;
        distinct.insert(raw & low23);
        nativeOK += Golay::decode23127(raw & low23) == input;
    }
    std::cout << aligned << ' ' << canonicalOK << ' ' << highBit << ' '
              << distinct.size() << ' ' << nativeOK << '\n';

    unsigned a, b;
    std::string frameHex;
    while (std::cin >> a >> b >> frameHex) {
        if (a >= 4096 || b >= 4096 || frameHex.size() != 18) return 1;
        std::array<uint8_t, 9> frame;
        for (size_t i = 0; i < frame.size(); ++i)
            frame[i] = std::stoul(frameHex.substr(i * 2, 2), nullptr, 16);
        char info[49];
        decode_ambe_frame(frame.data(), info);
        unsigned recovered = 0;
        for (unsigned i = 12; i < 24; ++i)
            recovered = (recovered << 1) | info[i];
        unsigned encodedA = std::stoul(frameHex.substr(0, 6), nullptr, 16);
        unsigned recoveredA = Golay::decode24128(encodedA);
        unsigned raw = Golay::encode23127(b);
        unsigned txMask = compute_prng_mask_23bit(a);
        unsigned rxMask = compute_prng_mask_23bit(recoveredA);
        unsigned wire = std::stoul(frameHex.substr(6, 6), nullptr, 16) >> 1;
        unsigned received = wire ^ rxMask;
        unsigned canonical = Golay::encode24128(b) >> 1;
        std::cout << raw << ' ' << canonical << ' ' << encodedA << ' ' << recoveredA
                  << ' ' << txMask << ' ' << rxMask << ' ' << (raw ^ txMask)
                  << ' ' << wire << ' ' << received << ' ' << Golay::decode23127(received)
                  << ' ' << recovered << ' ' << Golay::decode23127(canonical) << '\n';
    }
}
