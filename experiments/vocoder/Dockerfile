FROM rust:1.85-bookworm@sha256:e51d0265072d2d9d5d320f6a44dde6b9ef13653b035098febd68cce8fa7c0bc4
RUN apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*
WORKDIR /lab
RUN git clone https://github.com/MW0MWZ/OpenDMR.git opendmr && cd opendmr && git checkout d28164b39ba4d91ad5948ff22707937f8944f70f && make -j2
RUN git clone https://github.com/OpenBLIP25/blip25-vocoder.git blip25 && cd blip25 && git checkout d1762813b7142c021f4105c832bf7f060d1249fa
COPY opendmr-worker.cpp ./
RUN g++ -O2 -std=c++17 -Iopendmr opendmr-worker.cpp opendmr/libopendmr.a -lm -o opendmr-worker
COPY rust-worker ./rust-worker
RUN cargo build --locked --release --manifest-path rust-worker/Cargo.toml
COPY bench.py ./
COPY test_workers.py ./
RUN curl -fL https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav -o speech.wav && echo 'a4bf9becd046d7aedb6d05b6e12347a6294a44f74d263089c636fb0a2b1e6561  speech.wav' | sha256sum -c -
RUN mkdir /results && chmod 777 /results
USER 1000:1000
CMD ["python3", "bench.py", "--soak", "600"]
