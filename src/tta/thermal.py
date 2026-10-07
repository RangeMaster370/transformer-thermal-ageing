"""Transformer hot-spot temperature and insulation ageing following the IEC 60076-7 loading guide.

Steady state and the difference-equation (dynamic) method are implemented with the same
parameter set, so the dynamic model must settle on the steady-state value for a constant load.
Parameter values are typical ONAN distribution-transformer values used as stated assumptions.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Transformer:
    rating_kva: float = 630.0
    x: float = 0.8            # oil exponent
    y: float = 1.6            # winding exponent
    R: float = 5.0            # load-loss / no-load-loss ratio at rated current
    d_theta_or: float = 55.0  # top-oil rise over ambient at rated load (K)
    hgr: float = 23.0         # hot-spot factor x average winding-to-oil gradient (K)
    k11: float = 1.0
    k21: float = 1.0
    k22: float = 2.0
    tau_o: float = 180.0      # oil time constant (min)
    tau_w: float = 4.0        # winding time constant (min)
    upgraded_paper: bool = False


NORMAL_CYCLIC = {"hot_spot_c": 120.0, "top_oil_c": 105.0, "current_pu": 1.5}
LONG_EMERGENCY = {"hot_spot_c": 140.0, "top_oil_c": 115.0, "current_pu": 1.8}


def steady_state(K, theta_a, t: Transformer = Transformer()):
    """Top-oil and hot-spot temperature (degC) for per-unit load K at ambient theta_a."""
    K = np.asarray(K, dtype=float)
    top_rise = t.d_theta_or * ((1 + t.R * K ** 2) / (1 + t.R)) ** t.x
    top = theta_a + top_rise
    return top, top + t.hgr * K ** t.y


def dynamic(K, theta_a, dt_min=1.0, t: Transformer = Transformer(), init=None):
    """Difference-equation solution. K, theta_a: arrays per time step of dt_min minutes.

    Returns top-oil and hot-spot temperature arrays. Starts from the steady state of the first
    step unless init=(theta_o, d_h1, d_h2) is given.
    """
    K = np.asarray(K, dtype=float)
    ta = np.broadcast_to(np.asarray(theta_a, dtype=float), K.shape)
    n = len(K)
    th_o = np.empty(n)
    th_h = np.empty(n)
    if init is None:
        o0, _ = steady_state(K[0], ta[0], t)
        d1 = t.k21 * t.hgr * K[0] ** t.y
        d2 = (t.k21 - 1) * t.hgr * K[0] ** t.y
    else:
        o0, d1, d2 = init
    o = float(o0)
    if t.k21 == 1.0:
        d1, d2 = d1, d2
    for i in range(n):
        k, a = K[i], ta[i]
        o += dt_min / (t.k11 * t.tau_o) * (((1 + k * k * t.R) / (1 + t.R)) ** t.x * t.d_theta_or - (o - a))
        d1 += dt_min / (t.k22 * t.tau_w) * (t.k21 * t.hgr * k ** t.y - d1)
        d2 += dt_min / ((1 / t.k22) * t.tau_o) * ((t.k21 - 1) * t.hgr * k ** t.y - d2)
        th_o[i] = o
        th_h[i] = o + d1 - d2
    return th_o, th_h


def relative_ageing(theta_h, t: Transformer = Transformer()):
    """Relative ageing rate V (1 at the reference hot spot: 98 degC normal, 110 degC upgraded paper)."""
    th = np.asarray(theta_h, dtype=float)
    if t.upgraded_paper:
        return np.exp(15000.0 / (110.0 + 273.0) - 15000.0 / (th + 273.0))
    return 2.0 ** ((th - 98.0) / 6.0)


def loss_of_life_days(theta_h, dt_min, t: Transformer = Transformer()):
    """Equivalent days of life consumed over the series (one day at reference hot spot = 1)."""
    return float(np.sum(relative_ageing(theta_h, t)) * dt_min / 1440.0)


def limits_ok(top, hot, K, limits=NORMAL_CYCLIC):
    return bool(np.max(hot) <= limits["hot_spot_c"] and np.max(top) <= limits["top_oil_c"]
                and np.max(K) <= limits["current_pu"])
