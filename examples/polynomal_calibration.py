"""
CLI Utility for Multipoint Polynomial Calibration of Triton2 Sensors.
This script collects raw capacitance values at user-defined reference points,
averages them over a 2-second window, and calculates a polynomial fit.
The resulting calibration is saved to a JSON file for future use.
"""

import time
import json
import numpy as np
from datetime import datetime
from triton2 import Triton2Client, ChannelStreamReader, Channel

def get_channel_enum(ch_num: int) -> Channel:
    """Mapping integer channel to raw channel enum."""
    mapping = {
        1: Channel.CH1_RAW,
        2: Channel.CH2_RAW,
        3: Channel.CH3_RAW,
        4: Channel.CH4_RAW
    }
    return mapping.get(ch_num, Channel.CH1_RAW)

def save_calibration_json(filename, coeffs, raw_points, ref_points, channel, degree):
    """Saves the calibration data to a JSON file."""
    data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "sensor_type": "Triton2",
            "channel": channel,
            "polynomial_degree": degree
        },
        "calibration": {
            "coefficients": coeffs.tolist(),
            "formula": f"Sum(c[i] * x^(degree-i))"
        },
        "data_points": [
            {"raw_pf": raw, "reference": ref} 
            for raw, ref in zip(raw_points, ref_points)
        ]
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"\nCalibration saved successfully to: {filename}")

def run_calibration_cli():
    print("=" * 50)
    print(" Triton2 Multipoint Polynomial Calibration ")
    print("=" * 50)

    # 1. Connection Setup
    port = input("Enter Serial Port (e.g., COM3 or /dev/ttyUSB0): ").strip()
    slave_id = int(input("Enter Slave ID [default 1]: ") or "1")
    channel_num = int(input("Enter Channel to calibrate (1-4) [default 1]: ") or "1")
    poly_degree = int(input("Enter Polynomial Degree (e.g., 2 for quadratic) [default 2]: ") or "2")
    
    raw_points = []
    ref_points = []
    
    target_channel = get_channel_enum(channel_num)

    try:
        with Triton2Client(port, slave=slave_id) as client:
            print(f"\nConnected to Triton2 on {port} (Slave {slave_id})")
            print(f"Firmware: v{client.read_firmware_version():.2f}")
            
            while True:
                print(f"\n--- Point {len(ref_points) + 1} ---")
                try:
                    ref_input = input(f"Enter known reference value (e.g. liters, %) [or 'q' to finish]: ").lower().strip()
                    if ref_input == 'q':
                        if len(ref_points) < 2:
                            print("Error: At least 2 points are required for calibration.")
                            continue
                        break
                    
                    ref_val = float(ref_input)
                except ValueError:
                    print("Invalid input. Please enter a number or 'q'.")
                    continue

                print(f"Reading raw data for 2 seconds. Please keep level steady...")
                
                # Use StreamReader for high-speed sampling and averaging
                reader = ChannelStreamReader(client, channels=[target_channel])
                reader.read_for(2.0) # 2 seconds of sampling
                
                # Extract the raw column (index 1 in to_numpy results, index 0 is timestamp)
                samples = reader.to_numpy()
                if samples.size > 0:
                    avg_raw = np.mean(samples[:, 1])
                    std_raw = np.std(samples[:, 1])
                    
                    print(f"Captured {len(samples)} samples.")
                    print(f"Average Raw: {avg_raw:.4f} pF (StdDev: {std_raw:.4f})")
                    
                    raw_points.append(avg_raw)
                    ref_points.append(ref_val)
                    print(f"Point registered: Raw={avg_raw:.2f} -> Ref={ref_val:.2f}")
                else:
                    print("Error: No samples were collected. Check connection.")

                if len(ref_points) >= 2:
                    choice = input("\nAdd another point? (y/n): ").lower().strip()
                    if choice != 'y':
                        break

            # 2. Compute Calibration
            print("\n" + "=" * 50)
            print(" CALCULATING CALIBRATION ")
            print("=" * 50)
            
            # Use polyfit: we want to find Ref = f(Raw)
            coeffs = np.polyfit(raw_points, ref_points, poly_degree)
            poly_func = np.poly1d(coeffs)
            
            print(f"Polynomial Coefficients (Degree {poly_degree}):")
            print(coeffs)

            # 3. Save to JSON
            save_choice = input("\nSave this calibration to a JSON file? (y/n): ").lower().strip()
            if save_choice == 'y':
                default_filename = f"calibration_ch{channel_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filename = input(f"Enter filename [default: {default_filename}]: ").strip() or default_filename
                save_calibration_json(filename, coeffs, raw_points, ref_points, channel_num, poly_degree)
            
            # 4. Validation / Live Test
            print("\nStarting live calibrated view. Press Ctrl+C to stop.")
            try:
                while True:
                    current_raw = client.read_raw(channel_num)
                    calibrated = poly_func(current_raw)
                    print(f"\rRaw: {current_raw:7.2f} pF | Calibrated: {calibrated:7.2f}", end="", flush=True)
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n\nCalibration session ended.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    run_calibration_cli()