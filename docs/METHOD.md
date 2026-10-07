# Method and assumptions

## Thermal model (IEC 60076-7 loading guide)
- **Steady state**: top oil θo = θa + Δθor·((1 + R·K²)/(1 + R))^x; hot spot θh = θo + Hgr·K^y.
- **Dynamic**: the guide's difference equations with time step 1 min: top oil with oil time constant τo and k11; hot-spot gradient as the difference of two first-order terms (k21, k22, τw, τo). Each day is simulated three times and the last day is kept, so the initial state does not matter.
- **Ageing**: relative ageing V = 2^((θh − 98)/6) for non-thermally-upgraded paper (V = 1 at 98 °C, doubling every 6 K); the thermally upgraded law (reference 110 °C) is also implemented. Life used = ∫V dt, in days.
- **Limits** (normal cyclic loading, distribution transformers): 120 °C hot spot, 105 °C top oil, 1.5 pu current.

## Parameters (typical ONAN values, assumed)
| Symbol | Value | Meaning |
|---|---|---|
| x / y | 0.8 / 1.6 | oil / winding exponent |
| R | 5 | load-loss to no-load-loss ratio |
| Δθor | 55 K | top-oil rise at rated load |
| Hgr | 23 K | hot-spot to top-oil gradient at rated load |
| k11, k21, k22 | 1, 1, 2 | thermal model constants |
| τo / τw | 180 / 4 min | oil / winding time constants |

## Scenarios (synthetic)
- 180 households with morning and evening peaks (winter scale 1.25, summer 0.85); 300 kWp of rooftop PV; ambient 2 ± 4 °C (winter) and 22 ± 8 °C (summer).
- EVs: arrival ~ N(18:00, 1.5 h), 6-20 kWh each, 11 kW chargers. Shifted mode: same energy, start between 22:00 and 02:00, 7.4 kW.
- Battery: 250 kWh / 125 kW, discharges above 90 % of rated power, recharges below 60 %.
- Per-unit current from |net power| / (0.95 × 630 kVA), so reverse PV flow also loads the transformer.

## Verification (tests/test_thermal.py)
Rated load at 20 °C gives 75/98 °C; the dynamic model settles on the steady state at three loads and ambients; top oil reaches 1 − 1/e of its step after one oil time constant; ageing doubles every 6 K and equals 1 at 98 °C (110 °C for upgraded paper); a day at 98 °C uses one day of life; EV energy is conserved when shifted; battery state of charge stays within capacity; shifted charging lowers ageing; hosting capacity is a clean boundary.

## Results to note
- In winter the **1.5 pu current limit binds before the hot-spot limit** (cold ambient keeps the hot spot at 109 °C even at 1.72 pu), so the battery adds 30 EVs of capacity while shifted charging removes the evening peak entirely.
- Ageing is very non-linear: 160 uncontrolled EVs use 0.135 days of life per winter day, shifted charging 0.0019.

## Limits and next steps
No nameplate data or heat-run validation; no LV feeder voltage or cable limits; one representative day per season, not an annual ageing simulation; simple rule-based battery dispatch. Next: fit parameters to a real heat-run report, run a year of measured profiles, and add the feeder voltage limits from the grid-connection study.
