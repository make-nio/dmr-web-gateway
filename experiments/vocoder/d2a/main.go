package main

import (
    "encoding/hex"
    "encoding/json"
    "fmt"
    "os"

    "github.com/USA-RedDragon/dmrgo/v2/vocoder"
)

func main() {
    infoBytes, err := hex.DecodeString(os.Args[1])
    if err != nil || len(infoBytes) != 7 { panic("invalid literal length") }
    slotBytes, err := hex.DecodeString(os.Args[2])
    if err != nil || len(slotBytes) != 9 { panic("invalid slot length") }
    info := vocoder.AMBEFrame(infoBytes)
    encoded, err := vocoder.EncodeAMBE72(info)
    if err != nil { panic(err) }
    decoded, status := vocoder.DecodeAMBE72([9]byte(slotBytes))
    if err := json.NewEncoder(os.Stdout).Encode(map[string]any{
        "encodedSlot": fmt.Sprintf("%x", encoded), "decodedInfo": fmt.Sprintf("%x", decoded),
        "publishedInfoMatches": info == vocoder.AMBESilence(),
        "publishedSlotMatches": [9]byte(slotBytes) == vocoder.AMBESilenceSlot(),
        "status": status,
    }); err != nil { panic(err) }
}
