# Distribution transformer thermal loading and ageing study

A 630 kVA 20/0.4 kV ONAN secondary-substation transformer feeding 180 households with rooftop PV and a growing number of electric vehicles. The hot-spot and top-oil temperatures are computed with the IEC 60076-7 loading-guide thermal model (difference-equation method), insulation ageing with the guide's relative-ageing law, and the results are checked against the guide's normal cyclic loading limits. The study compares uncontrolled evening charging, charging shifted to the night, and uncontrolled charging with a 250 kWh / 125 kW battery for peak shaving.

| Question | Method | Result (see `results/REPORT.md`) |
|---|---|---|
| Is the thermal model right? | steady state vs dynamic model, guide relations | rated load at 20 °C gives 75 °C top oil and 98 °C hot spot; the dynamic model settles on the same value |
| How many EVs can the transformer take? | sweep of 0-200 EVs on a winter and a summer day against 120 °C hot spot, 105 °C top oil, 1.5 pu | winter: 120 EVs uncontrolled (current limit), 150 with the battery, 200+ with shifted charging |
| What does shifted charging do to ageing? | relative ageing integrated over a winter day with 160 EVs | life used per day drops from 0.135 to 0.0019 days (98.6 % less) |

## Run

```sh
pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 src/run_all.py        # regenerates results/ (a few seconds)
```

## Structure

```
src/tta/thermal.py    IEC 60076-7 steady-state and dynamic thermal model, ageing, loading limits
src/tta/scenarios.py  household, PV, EV and ambient profiles; battery peak-shaving rule
src/tta/study.py      daily runs, EV sweep, hosting capacity and binding limit
src/run_all.py        writes results/ (CSV, SVG, summary.json, REPORT.md, manifest.json)
tests/                11 checks
docs/METHOD.md        model, parameters, assumptions and limits
```

## Scope

Thermal parameters are typical ONAN distribution-transformer values used as assumptions, not a specific nameplate or heat-run test. Load, PV, EV and ambient profiles are synthetic. The model covers the transformer only (no cable or voltage limits on the LV feeder).
