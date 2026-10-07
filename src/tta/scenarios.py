"""Daily load scenarios for a 630 kVA 20/0.4 kV secondary-substation transformer.

Residential base load, rooftop PV, evening EV charging (uncontrolled or shifted) and a
battery used for peak shaving. All profiles are synthetic study assumptions at 1-minute steps.
"""
from __future__ import annotations

import numpy as np

STEPS = 1440            # one day at 1 min
H = np.arange(STEPS) / 60.0
HOUSEHOLDS = 180
RATING_KVA = 630.0
PF = 0.95


def base_load_kw(season="winter"):
    """Aggregated household demand (kW): morning and evening peaks, higher in winter."""
    per_house = (0.45 + 0.35 * np.exp(-((H - 7.5) / 1.3) ** 2) + 1.05 * np.exp(-((H - 19.0) / 2.0) ** 2)
                 + 0.25 * np.exp(-((H - 12.5) / 1.5) ** 2))
    scale = 1.25 if season == "winter" else 0.85
    return HOUSEHOLDS * per_house * scale


def pv_kw(kwp=300.0, season="summer"):
    if season == "winter":
        return kwp * 0.25 * np.clip(np.sin(np.pi * (H - 8.5) / 7.5), 0, None) ** 1.5
    return kwp * 0.78 * np.clip(np.sin(np.pi * (H - 5.5) / 15.0), 0, None) ** 1.5


def ev_kw(n_ev, mode="uncontrolled", seed=1, charger_kw=11.0):
    """Sum of EV charging power. Arrival ~ N(18.0 h, 1.5 h); energy 6-20 kWh per car.

    mode 'shifted': same energy, start delayed to a random time between 22:00 and 02:00
    and power limited to 7.4 kW (a simple time-of-use / grid-friendly charging rule).
    """
    rng = np.random.default_rng(seed)
    p = np.zeros(STEPS)
    for _ in range(n_ev):
        energy = rng.uniform(6, 20)
        if mode == "shifted":
            start, power = rng.uniform(22.0, 26.0) % 24, 7.4
        else:
            start, power = np.clip(rng.normal(18.0, 1.5), 14, 23), charger_kw
        dur_min = int(np.ceil(energy / power * 60))
        s = int(start * 60)
        idx = (s + np.arange(dur_min)) % STEPS
        p[idx] += power
    return p


def battery_peak_shave(net_kw, energy_kwh=250.0, power_kw=125.0, threshold_kw=None, soc0=0.5):
    """Discharge above a threshold, recharge below it; simple rule-based dispatch (1-min steps)."""
    if threshold_kw is None:
        threshold_kw = 0.9 * RATING_KVA * PF
    out = net_kw.copy()
    soc = soc0 * energy_kwh
    soc_trace = np.empty(STEPS)
    for i, p in enumerate(net_kw):
        if p > threshold_kw:
            d = min(p - threshold_kw, power_kw, soc * 60)
            out[i] -= d
            soc -= d / 60
        elif p < 0.6 * threshold_kw and soc < energy_kwh:
            c = min(power_kw, 0.6 * threshold_kw - p, (energy_kwh - soc) * 60)
            out[i] += c
            soc += c / 60
        soc_trace[i] = soc
    return out, soc_trace


def ambient(season="winter"):
    if season == "winter":
        return 2.0 + 4.0 * np.sin(np.pi * (H - 9) / 12).clip(-1, 1)
    return 22.0 + 8.0 * np.sin(np.pi * (H - 9) / 12).clip(-1, 1)


def per_unit(net_kw):
    """Per-unit transformer current from net active power (reverse flow counts as load too)."""
    return np.abs(net_kw) / PF / RATING_KVA
