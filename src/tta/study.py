"""Scenario runner: daily thermal response, limit checks and EV hosting capacity."""
from __future__ import annotations

import numpy as np

from . import scenarios as sc
from . import thermal as th

MODES = {"uncontrolled": ("uncontrolled", False), "shifted charging": ("shifted", False),
         "uncontrolled + battery": ("uncontrolled", True)}


def day(n_ev, mode="uncontrolled", season="winter", battery=False, pv_kwp=300.0, t=th.Transformer()):
    net = sc.base_load_kw(season) - sc.pv_kw(pv_kwp, season) + sc.ev_kw(n_ev, mode)
    soc = None
    if battery:
        net, soc = sc.battery_peak_shave(net)
    K = sc.per_unit(net)
    amb = sc.ambient(season)
    o, h = th.dynamic(np.tile(K, 3), np.tile(amb, 3), t=t)   # three identical days, keep the last
    o, h = o[-sc.STEPS:], h[-sc.STEPS:]
    return {"K": K, "ambient": amb, "top_oil": o, "hot_spot": h, "net_kw": net, "soc": soc,
            "K_max": float(K.max()), "hot_spot_max": float(h.max()), "top_oil_max": float(o.max()),
            "loss_of_life_days": th.loss_of_life_days(h, 1.0, t),
            "within_normal_cyclic": th.limits_ok(o, h, K)}


def sweep(season, counts=range(0, 201, 10)):
    rows = []
    for name, (mode, bat) in MODES.items():
        for n in counts:
            d = day(n, mode, season, bat)
            rows.append({"season": season, "mode": name, "n_ev": n, "K_max": d["K_max"],
                         "hot_spot_max": d["hot_spot_max"], "top_oil_max": d["top_oil_max"],
                         "loss_of_life_days": d["loss_of_life_days"], "ok": d["within_normal_cyclic"]})
    return rows


def binding_limit(r, limits=th.NORMAL_CYCLIC):
    hit = []
    if r["K_max"] > limits["current_pu"]:
        hit.append("current")
    if r["hot_spot_max"] > limits["hot_spot_c"]:
        hit.append("hot spot")
    if r["top_oil_max"] > limits["top_oil_c"]:
        hit.append("top oil")
    return ", ".join(hit)


def hosting_capacity(rows):
    """Largest EV count for which every count up to it stays within the normal cyclic limits.

    Returns {mode: {"ev": n, "limited_by": limit names or "sweep end"}}.
    """
    out = {}
    for mode in MODES:
        rs = sorted((r for r in rows if r["mode"] == mode), key=lambda r: r["n_ev"])
        cap, by = None, "sweep end"
        for r in rs:
            if not r["ok"]:
                by = binding_limit(r)
                break
            cap = r["n_ev"]
        out[mode] = {"ev": cap, "limited_by": by}
    return out
