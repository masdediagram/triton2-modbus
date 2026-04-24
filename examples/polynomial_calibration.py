"""
CLI Utility for Multipoint Polynomial Calibration of Triton2 Sensors.
This script collects raw capacitance values at user-defined reference points,
averages them over a 2-second window, and calculates a polynomial fit.
The resulting calibration is saved to a JSON file for future use.
"""
from triton2 import Channel, ChannelStreamReader, Triton2Client, DeviceScanner
import serial.tools.list_ports
import pandas as pd
import numpy as np
from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator
import json
from datetime import datetime

# Functions

def equation_str(coeffs)->str:
    # Unicode superscripts make printed equations easier to read in terminal output.
    SUB_MAP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    equation = ''

    for n, x in enumerate(coeffs):
        if n==0:
            equation += f" + ({x:.3E})"
        else:
            exponent = str(n).translate(SUB_MAP)
            equation += f" + ({x:.3E})x{exponent}"


    equation = "f(x) = " + equation.strip(" + ")
    return equation

def record(seconds:float, port, channels:list[Channel] = [Channel.CH1_RAW], device=1)->pd.DataFrame:
    # Open a temporary Modbus session, stream channel data, and return tabular samples.
    with Triton2Client(port, slave=device) as client:
        reader = ChannelStreamReader(client, channels=channels)
        reader.read_for(seconds)

        print(f"      Collected {len(reader)} samples")

        df = reader.to_dataframe()

    return df

def record_average(seconds, port, device=1)->float:
    # Calibration uses a short averaging window to reduce noise at each point.
    df = record(seconds, port, device=device)
    return float(df['ch1_raw'].mean())


def run_calibration():
    ## Scan COM ports

    ports = serial.tools.list_ports.comports()

    port_options = {f'{port.device} {port.description}':port.device for port in ports}

    if len(ports) > 1:
        # Ask the user when multiple serial ports are available.
        port_selector = inquirer.select(
            message="Select COM port:",
            choices=list(port_options.keys()),
        ).execute()

        PORT = port_options[port_selector]
    else:
        PORT = ports[0].device #Select COM port

    print(f"\nSelected port: {PORT}")

    ## Scan Triton devices in COM port

    with DeviceScanner(PORT, timeout=0.1, retries=0) as scanner:
        devices_found = scanner.scan(slave_ids=range(0, 10))

    if len(devices_found) == 0:
        # Exit early when no Modbus slave responds on the selected port.
        print("[ERROR] NO DEVICE FOUND!")
        print("Make sure that the device is connected correctly and the correct port is selected\n")
        print("EXITING...")
        return

    elif len(devices_found) > 1:
        # Let the user choose a specific slave when multiple devices are found.
        device_selector = inquirer.select(
            message="Select device:",
            choices=devices_found,
        ).execute()

        DEVICE = devices_found[device_selector]
    else:
        DEVICE = devices_found[0] #Select COM port

    print(f'Device: {DEVICE}')


    number_points = int(inquirer.number(
            message="Number of calibration points",
            min_allowed=2,
            max_allowed=10,
            validate=EmptyInputValidator(),
        ).execute())
    

    points = []

    print("\nSTARTING CALIBRATION\n")

    for i in range(number_points):
        
        print(f"    POINT {i+1}/{number_points}")

        float_val = float(inquirer.number(
            message=f"    Enter reference value for point {i+1}: ",
            float_allowed=True,
            validate=EmptyInputValidator(),
        ).execute())

        print('      Reading measurement...')
        # Capture a 5-second average of raw channel data for this reference point.
        raw = record_average(5, PORT, device=DEVICE)
        print(f'      Measurements average:{raw:.1f}')

        points.append([raw, float_val])
        print(f'      Point {i+1}: ({float_val:.3e}, {raw:.3e})\n')

    points = np.array(points)
    # Use linear fit for 2 points, quadratic otherwise (up to degree 2).
    degree = min(2, number_points-1)
    coefficients = np.polyfit(x=points[:,0], y=points[:,1], deg=degree)
    print("\nCALIBRATION FINISHED\n")

    print("Coefficients: ", coefficients)
    print(f"Polynomial degree: {degree}")
    equation = equation_str(coefficients.tolist())
    print("Polynomial:")
    print(equation)
    print()

    date = datetime.now()
    # Store enough metadata to reproduce and audit the calibration later.
    calibration_data = {
        'time':date.isoformat(),
        'points': {
            'raw-values':points[:,0],
            'reference-values':points[:,1]
        },
        'degree':degree,
        'coefficients':coefficients.tolist()
    }

    filepath = f"calibration-{date.strftime('%Y%m%d%H%M')}.json"
    # Save calibration output in the current working directory.
    with open(filepath, 'w') as f:
        json.dump(calibration_data, f)

    print(f"Calibration data saved in: {filepath}")


if __name__ == '__main__':
    run_calibration()