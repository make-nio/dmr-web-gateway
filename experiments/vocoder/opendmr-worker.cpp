#include "opendmr.h"
#include <chrono>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <vector>
#include <string>

int main() {
    auto encoder = opendmr_encoder_create();
    auto decoder = opendmr_decoder_create();
    if (!encoder || !decoder) return 2;
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line == "R") {
            opendmr_encoder_reset(encoder); opendmr_decoder_reset(decoder);
            std::cout << "0 " << std::endl; continue;
        }
        std::istringstream input(line);
        std::string operation, hex;
        input >> operation >> hex;
        if (!((operation=="E" && hex.size()==640)||(operation=="D" && hex.size()==18)) || hex.find_first_not_of("0123456789abcdefABCDEF")!=std::string::npos) {
            std::cout << "ERR" << std::endl; continue;
        }
        std::vector<uint8_t> bytes;
        for (size_t offset=0;offset<hex.size();offset+=2) bytes.push_back(std::stoul(hex.substr(offset,2),nullptr,16));
        int16_t pcm[160]; uint8_t frame[9]; int errors=0;
        auto start = std::chrono::steady_clock::now();
        bool ok;
        if (operation=="E") {
            for (size_t index=0;index<160;index++) pcm[index]=int16_t(uint16_t(bytes[2*index])|(uint16_t(bytes[2*index+1])<<8));
            ok=opendmr_encode(encoder,pcm,frame);
        } else ok=opendmr_decode(decoder,bytes.data(),pcm,&errors);
        auto nanos=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();
        if (!ok) {std::cout << "ERR" << std::endl;continue;}
        std::cout << std::dec << nanos << " ";
        if (operation=="E") {
            for (auto byte:frame) std::cout << std::hex << std::setw(2) << std::setfill('0') << unsigned(byte);
        } else {
            for (auto sample:pcm) for (int shift:{0,8}) std::cout << std::hex << std::setw(2) << std::setfill('0') << unsigned((uint16_t(sample)>>shift)&255);
        }
        std::cout << std::endl;
    }
    opendmr_encoder_destroy(encoder); opendmr_decoder_destroy(decoder);
}
