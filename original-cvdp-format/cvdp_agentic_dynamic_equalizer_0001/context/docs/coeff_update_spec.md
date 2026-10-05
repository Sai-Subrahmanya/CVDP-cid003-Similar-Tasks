# Coefficients Update Specification

## Overview
The `coeff_update` module computes the next coefficients of the filter based on the selected algorithm, using the corresponding update rule described in the `algorithms.md` file. The central tap of the real coefficients must be initialized to 1 in fixed-point notation, while all other coefficients must be initialized to 0.

Since division is very costly in hardware, the value of the learning rate parameter is used to apply bitwise shifts to the signal, effectively dividing it by two for each shift.

## Interface

### Signals Table
| Signal        | In/Out | Width | Parallelism | Description                                |
|---------------|--------|-------|-------------|--------------------------------------------|
| clk           | Input  | 1     | 1           | System clock                               |
| rst_n         | Input  | 1     | 1           | Asynchronous active-low reset              |
| data_real     | Input  | 16    | 7           | Real part of the input signals             |
| data_imag     | Input  | 16    | 7           | Imaginary part of the input signals        |
| error_real    | Input  | 16    | 1           | Real part of the error signal              |
| error_imag    | Input  | 16    | 1           | Imaginary part of the error signal         |
| coeff_real    | Output | 16    | 7           | Real part of the coefficients signals      |
| coeff_imag    | Output | 16    | 7           | Imaginary part of the coefficients signals |

### Parameters Table
| Parameter   | Value | Description                   |
|-------------|-------|-------------------------------|
| TAP_NUM     | 7     | Number of taps of the filters |
| DATA_WIDTH  | 16    | Bit width of the data         |
| COEFF_WIDTH | 16    | Bit width of the coefficients |
| MU          | 15    | Learning rate                 |