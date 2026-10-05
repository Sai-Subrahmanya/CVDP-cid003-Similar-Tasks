# Dynamic Equalizer Specification

## Overview
A dynamic equalizer is designed to adaptively compensate for channel impairments such as inter-symbol interference (ISI) and signal distortion in real-time digital communication systems. It employs adaptive filtering techniques, such as Least Mean Squares (LMS) and Constant Modulus Algorithm(CMA), to continuously adjust its internal tap coefficients based on the error between the received signal and a reference signal. This allows the equalizer to dynamically "learn" and correct channel effects without prior knowledge of the distortion profile. The architecture typically includes a shift register for sample history, multipliers for tap-weighted inputs, an accumulator for the filter output, and logic for error calculation and coefficient updates. Over time, the equalizer converges such that its output closely matches the desired signal, improving signal fidelity and reducing bit error rates in high-speed data links.

The equation used to calculate the output of the dynamic equalizer for complex baseband signals is as follows:

\[
\hat{y}[n] = \sum_{k=0}^{L-1} w_k[n] \cdot x[n-k]
\]

- \( \hat{y}[n] \) = Equalizer output at time \( n \)  
- \( w_k[n] \) = Complex-valued filter tap coefficient at time \( n \)  
- \( x[n-k] \) = Complex input sample (includes I and Q)

The equalizer has two internal modules: `error_calc`, which computes the error based on the selected algorithm, and `coeff_update`, which calculates the filter coefficients to be used in the next cycle.

The `desired_real` and `desired_imag` signals are only used when the LMS algorithm is selected, as the other algorithms do not require the desired signal data as input.

## Interface

### Signals Table
| Signal        | In/Out | Width | Description                          |
|---------------|--------|-------|--------------------------------------|
| clk           | Input  | 1     | System clock                         |
| rst_n         | Input  | 1     | Asynchronous active-low reset        |
| data_in_real  | Input  | 16    | Real part of the input signal        |
| data_in_imag  | Input  | 16    | Imaginary part of the input signal   |
| desired_real  | Input  | 16    | Real part of the desired signal      |
| desired_imag  | Input  | 16    | Imaginary part of the desired signal |
| data_out_real | Output | 16    | Real part of the output signal       |
| data_out_imag | Output | 16    | Imaginary part of the output signal  |

### Parameters Table
| Parameter   | Value | Description                   |
|-------------|-------|-------------------------------|
| TAP_NUM     | 7     | Number of taps of the filters |
| DATA_WIDTH  | 16    | Bit width of the data         |
| COEFF_WIDTH | 16    | Bit width of the coefficients |
| MU          | 15    | Learning rate                 |