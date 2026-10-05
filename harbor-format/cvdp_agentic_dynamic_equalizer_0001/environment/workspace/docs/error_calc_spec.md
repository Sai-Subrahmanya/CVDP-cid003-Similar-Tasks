# Error Calculation Specification

## Overview
The `error_calc` module computes the error based on the selected algorithm, using the corresponding equation described in the `algorithms.md` file.

The `desired_real` and `desired_imag` signals are only used when the LMS algorithm is selected, as the other algorithms do not require the desired signal data as input. For the other algorithms, since they are intended for QPSK, the reference signal R is set to 1.

## Interface

### Signals Table
| Signal        | In/Out | Width | Description                          |
|---------------|--------|-------|--------------------------------------|
| data_real     | Input  | 16    | Real part of the input signal        |
| data_imag     | Input  | 16    | Imaginary part of the input signal   |
| desired_real  | Input  | 16    | Real part of the desired signal      |
| desired_imag  | Input  | 16    | Imaginary part of the desired signal |
| error_real    | Output | 16    | Real part of the error signal        |
| error_imag    | Output | 16    | Imaginary part of the error signal   |

### Parameters Table
| Parameter   | Value | Description                   |
|-------------|-------|-------------------------------|
| DATA_WIDTH  | 16    | Bit width of the data         |