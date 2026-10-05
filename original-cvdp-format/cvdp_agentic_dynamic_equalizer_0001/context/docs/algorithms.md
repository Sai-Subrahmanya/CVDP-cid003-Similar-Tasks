### **1. LMS (Least Mean Squares) Algorithm**

The **LMS algorithm** is a widely used adaptive filtering technique that adjusts filter coefficients to minimize the **mean squared error** between the filter's output and a desired signal.

#### How it works:
- At each iteration, the filter output is calculated as the dot product of the input vector and filter coefficients.
- The **error** is computed as:
  \[
  e(n) = d(n) - y(n)
  \]
  where `d(n)` is the desired signal and `y(n)` is the filter output.
- The filter coefficients are updated as:
  \[
  w(n+1) = w(n) + \mu \cdot e(n) \cdot x(n)
  \]
  where:
  - `w(n)` is the coefficient vector
  - `x(n)` is the input vector
  - `μ` is the step size (learning rate)

LMS is **simple, stable, and converges slowly** depending on `μ`.

---

### **2. CMA (Constant Modulus Algorithm)**

**CMA** is a **blind equalization** algorithm — it does **not require a training signal**. It assumes that the transmitted signal has a **constant modulus** (magnitude), such as in QPSK or PSK systems.

#### How it works:
- The algorithm minimizes the cost function:
  \[
  J(n) = \left(|y(n)|^2 - R\right)^2
  \]
  where `R` is a constant related to the signal’s expected modulus.
- The error used to update the coefficients is:
  \[
  e(n) = y(n) \cdot \left(|y(n)|^2 - R\right)
  \]
- The weights are updated as:
  \[
  w(n+1) = w(n) - \mu \cdot e(n) \cdot x^*(n)
  \]

CMA is useful for **equalizing signals blindly**, but can suffer from **phase ambiguity**.

---

### **3. MCMA (Multimodulus CMA)**

**MCMA** is an extension of CMA tailored for **higher-order QAM constellations** (e.g., 16-QAM), where symbols do **not all have the same modulus**.

#### How it works:
- It separately controls the **real** and **imaginary** parts:
  \[
  e_{\text{real}} = y_{\text{real}} \cdot (|y_{\text{real}}|^2 - R_{\text{real}})
  \]
  \[
  e_{\text{imag}} = y_{\text{imag}} \cdot (|y_{\text{imag}}|^2 - R_{\text{imag}})
  \]
- The total error is combined, and the weights are updated:
  \[
  w(n+1) = w(n) - \mu \cdot (e_{\text{real}} + j \cdot e_{\text{imag}}) \cdot x^*(n)
  \]

MCMA improves convergence and performance on **non-constant modulus signals**, such as QAM.

---

### **4. RDE (Radius Directed Equalizer)**

**RDE** is another blind equalization method, similar to CMA, but instead of pushing all symbols to a constant modulus, it tries to force them onto a **circle with radius `R`** — typically better suited for circular constellations.

#### How it works:
- It minimizes:
  \[
  J(n) = \left(|y(n)| - R\right)^2
  \]
- The gradient (error) is:
  \[
  e(n) = \left(1 - \frac{R}{|y(n)|}\right) \cdot y(n)
  \]
- Update rule:
  \[
  w(n+1) = w(n) - \mu \cdot e(n) \cdot x^*(n)
  \]

RDE provides better convergence in some cases and can be more robust for **radial symmetry constellations**.