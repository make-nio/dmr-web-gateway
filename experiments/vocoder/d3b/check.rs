use blip25_vocoder::halfrate::frame::{decode_code_vectors, encode_code_vectors};
use std::io::{self, Read};

fn main() {
    let mut data = Vec::new();
    io::stdin().read_to_end(&mut data).unwrap();
    assert_eq!(data.len(), 9000);
    for frame in data.chunks_exact(9) {
        let mut pos = 0;
        let mut words = [0u32; 4];
        for (word, width) in words.iter_mut().zip([24, 23, 11, 14]) {
            for _ in 0..width {
                *word = (*word << 1) | u32::from((frame[pos/8] >> (7-pos%8)) & 1);
                pos += 1;
            }
        }
        let decoded = decode_code_vectors(words);
        for (value, width) in decoded.info.iter().zip([12, 12, 11, 14]) {
            print!("{:0width$b}", value, width=width);
        }
        println!(" {} {}", decoded.error_total(), encode_code_vectors(&decoded.info) == words);
    }
}
