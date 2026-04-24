# Polynomial Calibration Script

This guide explains how to run `examples/polynomial_calibration.py` to generate a polynomial calibration file from measured Triton2 raw values and known reference points.

## Requirements

- Python environment with this project installed
- A connected Triton2 device
- Required prompt library:

```bash
pip install inquirer
```

## Run the Script

From the repository root:

```bash
python examples/polynomial_calibration.py
```

## What the Script Does

1. Scans available COM ports and asks you to choose one (if more than one is found).
2. Scans device IDs on the selected port and asks you to choose a device (if more than one is found).
3. Prompts for the number of calibration points (minimum 2, maximum 10).
4. For each point:
   - You enter the known reference value.
   - The script samples raw channel data and computes the average measurement.
   - The `(raw_average, reference_value)` point is stored.
5. Fits a polynomial using the collected points:
   - Degree 1 for 2 points
   - Degree 2 for 3 or more points
6. Prints coefficients and the resulting polynomial equation.
7. Saves calibration output to a timestamped JSON file like:

`calibration-YYYYMMDDHHMM.json`

## Output File Contents

The generated JSON file includes:

- `time`: ISO timestamp of calibration run
- `points.raw-values`: measured raw averages
- `points.reference-values`: entered reference values
- `degree`: polynomial degree used
- `coefficients`: polynomial coefficients

## Tips

- Keep the sensor in a stable condition during each measurement step.
- Use well-distributed reference values across your expected operating range.
- If no devices are found, verify wiring, power, and COM port selection.
