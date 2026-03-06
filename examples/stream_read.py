"""High-speed stream reading: collect samples, then export to numpy or CSV."""

import sys
from pathlib import Path

if (Path(__file__).resolve().parent.parent / "src").is_dir():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from triton2 import Channel, ChannelStreamReader, Triton2Client

PORT = "COM3"
NUM_SAMPLES = 100

with Triton2Client(PORT, slave=1) as client:
    reader = ChannelStreamReader(client, channels=[Channel.CH1_CAL, Channel.CH2_CAL, Channel.CH3_CAL, Channel.CH4_CAL])
    reader.read_n(NUM_SAMPLES)

    print(f"Collected {len(reader)} samples")
    print("Columns:", reader.column_names)
    print("First row:", reader.to_numpy()[0])

    reader.to_csv("triton2_stream.csv")
    print("Saved to triton2_stream.csv")
