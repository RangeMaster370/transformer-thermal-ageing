# Results report

Python implementation of the IEC 60076-7 thermal model with typical ONAN distribution-transformer parameters and synthetic load, PV, EV and ambient profiles (study assumptions).

Rated load at 20 °C: top oil 75.0 °C, hot spot 98.0 °C (dynamic model settles at 98.00 °C).

## EV hosting capacity (normal cyclic limits: 120 °C hot spot, 105 °C top oil, 1.5 pu)

| Charging | Winter | Summer |
|---|---|---|
| uncontrolled | 120 (current) | 160 (current) |
| shifted charging | 200+ (end of sweep) | 200+ (end of sweep) |
| uncontrolled + battery | 150 (current) | 200+ (end of sweep) |

## Winter day with 160 EVs

| Charging | Peak load (pu) | Peak hot spot (°C) | Life used (days) | Within limits |
|---|---|---|---|---|
| uncontrolled | 1.722 | 108.8 | 0.135 | False |
| shifted charging | 1.1 | 65.7 | 0.0019 | True |
| uncontrolled + battery | 1.514 | 95.8 | 0.0277 | False |
