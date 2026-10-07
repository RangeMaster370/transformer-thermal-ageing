"""Numerical checks of the IEC 60076-7 thermal and ageing implementation and the study logic."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tta import scenarios as sc, study, thermal as th  # noqa: E402

T = th.Transformer()


class Thermal(unittest.TestCase):
    def test_rated_load_at_20c_gives_98c_hot_spot(self):
        top, hot = th.steady_state(1.0, 20.0, T)
        self.assertAlmostEqual(float(top), 75.0, places=9)   # 20 + 55 K top-oil rise
        self.assertAlmostEqual(float(hot), 98.0, places=9)   # + 23 K hot-spot gradient

    def test_dynamic_settles_on_steady_state(self):
        for K, amb in ((0.6, 10.0), (1.0, 20.0), (1.3, 30.0)):
            o, h = th.dynamic(np.full(5000, K), amb, t=T, init=(amb, 0.0, 0.0))
            so, sh = th.steady_state(K, amb, T)
            self.assertAlmostEqual(o[-1], float(so), places=3)
            self.assertAlmostEqual(h[-1], float(sh), places=3)

    def test_step_response_time_constant(self):
        # after one oil time constant the top-oil rise reaches 1 - 1/e of its final change
        o, _ = th.dynamic(np.full(int(T.tau_o), 1.0), 20.0, t=T, init=(20.0, 0.0, 0.0))
        frac = (o[-1] - 20.0) / 55.0
        self.assertAlmostEqual(frac, 1 - np.exp(-1), delta=0.01)

    def test_ageing_doubles_every_6k(self):
        self.assertAlmostEqual(float(th.relative_ageing(98.0)), 1.0)
        self.assertAlmostEqual(float(th.relative_ageing(104.0)), 2.0)
        self.assertAlmostEqual(float(th.relative_ageing(92.0)), 0.5)

    def test_upgraded_paper_reference_110c(self):
        up = th.Transformer(upgraded_paper=True)
        self.assertAlmostEqual(float(th.relative_ageing(110.0, up)), 1.0)

    def test_constant_98c_for_a_day_uses_one_day(self):
        self.assertAlmostEqual(th.loss_of_life_days(np.full(1440, 98.0), 1.0, T), 1.0)

    def test_hot_spot_rises_with_load(self):
        _, h = th.steady_state(np.array([0.5, 1.0, 1.5]), 20.0, T)
        self.assertTrue(np.all(np.diff(h) > 0))


class Study(unittest.TestCase):
    def test_ev_energy_conserved_when_shifted(self):
        a = sc.ev_kw(50, "uncontrolled").sum() / 60
        b = sc.ev_kw(50, "shifted").sum() / 60
        self.assertAlmostEqual(a, b, delta=0.08 * a)     # rounding to whole minutes per car

    def test_battery_never_exceeds_capacity_and_lowers_peak(self):
        net = sc.base_load_kw("winter") + sc.ev_kw(160)
        out, soc = sc.battery_peak_shave(net, energy_kwh=250, power_kw=125)
        self.assertTrue(np.all(soc >= -1e-9) and np.all(soc <= 250 + 1e-9))
        self.assertLess(out.max(), net.max())

    def test_shifted_charging_reduces_ageing(self):
        u = study.day(160, "uncontrolled", "winter")
        s = study.day(160, "shifted", "winter")
        self.assertLess(s["loss_of_life_days"], u["loss_of_life_days"])
        self.assertLess(s["hot_spot_max"], u["hot_spot_max"])

    def test_hosting_capacity_is_monotone_boundary(self):
        rows = study.sweep("winter", counts=range(0, 201, 20))
        cap = study.hosting_capacity(rows)
        for mode, c in cap.items():
            for r in rows:
                if r["mode"] == mode and c["ev"] is not None and r["n_ev"] <= c["ev"]:
                    self.assertTrue(r["ok"], (mode, r["n_ev"]))


if __name__ == "__main__":
    unittest.main()
