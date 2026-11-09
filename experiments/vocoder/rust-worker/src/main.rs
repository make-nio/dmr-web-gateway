use blip25_vocoder::vocoder::{Vocoder, Rate, FrameStatus};
use blip25_vocoder::halfrate::frame::{encode_code_vectors, decode_code_vectors};
use std::io::{self, BufRead, Write};
use std::time::Instant;

fn main() {
    let mut encoder = Vocoder::new(Rate::HalfRate3600x2450);
    let mut decoder = Vocoder::new(Rate::HalfRate3600x2450);
    for line in io::stdin().lock().lines() {
        let line = line.unwrap();
        if line == "R" {
            encoder = Vocoder::new(Rate::HalfRate3600x2450);
            decoder = Vocoder::new(Rate::HalfRate3600x2450);
            println!("0 "); io::stdout().flush().unwrap(); continue;
        }
        let (op, hex) = line.split_once(' ').unwrap_or(("", ""));
        if !hex.is_ascii() || hex.len()%2 != 0 { println!("ERR"); continue; }
        let bytes: Result<Vec<u8>,_> = (0..hex.len()).step_by(2).map(|offset|u8::from_str_radix(&hex[offset..offset+2],16)).collect();
        let Ok(bytes) = bytes else {println!("ERR");continue;};
        if !((op=="E" && bytes.len()==320)||(op=="D" && bytes.len()==9)) {println!("ERR");continue;}
        let start = Instant::now();
        let output: Vec<u8>;
        if op == "E" {
            let pcm: Vec<i16> = bytes.chunks_exact(2).map(|pair|i16::from_le_bytes([pair[0],pair[1]])).collect();
            let info: [u16;4] = encoder.encode_info(&pcm).unwrap().try_into().unwrap();
            let vectors = encode_code_vectors(&info);
            let mut bits = Vec::new();
            for (word,width) in vectors.iter().zip([24,23,11,14]) {
                for shift in (0..width).rev() {bits.push(((word>>shift)&1) as u8);}
            }
            output = bits.chunks_exact(8).map(|chunk|chunk.iter().fold(0,|value,bit|(value<<1)|bit)).collect();
        } else {
            let mut offset = 0;
            let mut vectors = [0u32;4];
            for (word,width) in vectors.iter_mut().zip([24,23,11,14]) {
                for _ in 0..width { *word=(*word<<1)|u32::from((bytes[offset/8]>>(7-offset%8))&1); offset+=1; }
            }
            let frame = decode_code_vectors(vectors);
            output = decoder.decode_info(&frame.info,FrameStatus::new(u32::from(frame.error_total()),false)).unwrap().iter().flat_map(|sample|sample.to_le_bytes()).collect();
        }
        let nanos = start.elapsed().as_nanos();
        println!("{} {}",nanos,output.iter().map(|byte|format!("{byte:02x}")).collect::<String>());
        io::stdout().flush().unwrap();
    }
}
