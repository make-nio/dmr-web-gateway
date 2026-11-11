#include <cstdio>
#include <cstdlib>

extern "C" void __real_mbe_floattoshort(float*, short*);

extern "C" void __wrap_mbe_floattoshort(float* samples, short* pcm) {
    // The upstream CLI runs one continuous decoder in this process.
    static FILE* capture = std::fopen("/tmp/pre.f32le", "wb");
    if (!capture || std::fwrite(samples, sizeof(float), 160, capture) != 160 ||
        std::fflush(capture) != 0) std::abort();
    __real_mbe_floattoshort(samples, pcm);
}
