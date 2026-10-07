"""Run every study and regenerate results/. Keep all reported numbers in summary.json."""
import csv
import hashlib
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "results"

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from tta import scenarios as sc, study, thermal as th  # noqa: E402

BG, NAVY, TEAL, WARM, GREY, RED = "#FBFCFD", "#172D49", "#2F7F91", "#C8742F", "#7D8C96", "#A23B3B"
COL = {"uncontrolled": WARM, "shifted charging": TEAL, "uncontrolled + battery": NAVY}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#B9C6CF",
                     "axes.labelcolor": NAVY, "xtick.color": "#3D4B55", "ytick.color": "#3D4B55",
                     "axes.titlecolor": NAVY, "axes.titlesize": 13, "svg.hashsalt": "tta"})
CASE_EV = 160


def _fig(rows=1):
    fig, ax = plt.subplots(rows, 1, figsize=(9, 4.6), dpi=100, facecolor=BG, sharex=rows > 1)
    for a in np.atleast_1d(ax):
        a.set_facecolor(BG)
        a.grid(color="#DCE3EA", linewidth=0.8)
        a.spines[["top", "right"]].set_visible(False)
    return fig, ax


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, format="svg", facecolor=BG, metadata={"Date": None})
    plt.close(fig)
    t = path.read_text()
    path.write_text(re.sub(r'width="[\d.]+pt" height="[\d.]+pt"', 'width="900" height="460"', t, count=1))


def plot_day(cases, path):
    fig, (a1, a2) = _fig(2)
    h = np.arange(sc.STEPS) / 60
    for name, d in cases.items():
        a1.plot(h, d["K"], color=COL[name], lw=1.6, label=name)
        a2.plot(h, d["hot_spot"], color=COL[name], lw=1.8, label=name)
    a1.axhline(1.5, color=RED, ls="--", lw=1)
    a1.text(8, 1.56, "1.5 pu current limit", color=RED, fontsize=8.5)
    a1.set_ylabel("Load (pu)")
    a2.axhline(120, color=RED, ls="--", lw=1)
    a2.text(8, 112, "120 °C hot-spot limit", color=RED, fontsize=8.5)
    a2.set_ylabel("Hot spot (°C)")
    a2.set_xlabel("Hour of day")
    a2.set_xticks(range(0, 25, 3))
    a1.set_ylim(0, 1.95)
    a1.legend(frameon=False, ncol=3, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, 1.02))
    a1.set_title(f"Winter day, {CASE_EV} EVs on a 630 kVA transformer")
    _save(fig, path)


def plot_sweep(rows, cap, path, season):
    fig, ax = _fig()
    for name in study.MODES:
        r = [x for x in rows if x["mode"] == name]
        ax.plot([x["n_ev"] for x in r], [x["hot_spot_max"] for x in r], color=COL[name], lw=1.8, marker="o", ms=3,
                label=f"{name}: " + (f"{cap[name]['ev']} EVs ({cap[name]['limited_by']} limit)" if cap[name]["limited_by"] != "sweep end" else f"200+ EVs (end of sweep)"))
    ax.axhline(120, color=RED, ls="--", lw=1)
    ax.set_xlabel("Electric vehicles on the feeder")
    ax.set_ylabel("Daily peak hot spot (°C)")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    ax.set_title(f"EV hosting capacity, {season} day (IEC 60076-7 normal cyclic limits)")
    _save(fig, path)


def plot_ageing(rows, path):
    fig, ax = _fig()
    for name in study.MODES:
        r = [x for x in rows if x["mode"] == name]
        ax.semilogy([x["n_ev"] for x in r], [max(x["loss_of_life_days"], 1e-5) for x in r], color=COL[name], lw=1.8,
                    marker="o", ms=3, label=name)
    ax.axhline(1.0, color=GREY, ls="--", lw=1)
    ax.text(2, 1.25, "1 day of life per day (98 °C hot spot)", color=GREY, fontsize=8.5)
    ax.set_xlabel("Electric vehicles on the feeder")
    ax.set_ylabel("Life consumed per day (days)")
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("Insulation ageing per winter day (relative ageing integrated over 24 h)")
    _save(fig, path)


def main():
    OUT.mkdir(exist_ok=True)
    t = th.Transformer()
    rows = study.sweep("winter") + study.sweep("summer")
    with open(OUT / "hosting_sweep.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    cap = {s: study.hosting_capacity([r for r in rows if r["season"] == s]) for s in ("winter", "summer")}

    cases = {name: study.day(CASE_EV, mode, "winter", bat) for name, (mode, bat) in study.MODES.items()}
    with open(OUT / f"winter_day_{CASE_EV}ev.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["minute"] + [f"{n}_{k}" for n in cases for k in ("K", "hot_spot_c")])
        for i in range(sc.STEPS):
            w.writerow([i] + [round(float(cases[n][k][i]), 4) for n in cases for k in ("K", "hot_spot")])

    plot_day(cases, OUT / "winter_day.svg")
    plot_sweep([r for r in rows if r["season"] == "winter"], cap["winter"], OUT / "hosting_capacity.svg", "winter")
    plot_ageing([r for r in rows if r["season"] == "winter"], OUT / "ageing.svg")

    o, h = th.steady_state(1.0, 20.0, t)
    od, hd = th.dynamic(np.full(4000, 1.0), 20.0, t=t, init=(20.0, 0.0, 0.0))
    summary = {
        "provenance": "Python implementation of the IEC 60076-7 thermal model with typical ONAN distribution-"
                      "transformer parameters and synthetic load, PV, EV and ambient profiles (study assumptions).",
        "transformer": {k: getattr(t, k) for k in ("rating_kva", "x", "y", "R", "d_theta_or", "hgr", "tau_o", "tau_w")},
        "limits_normal_cyclic": th.NORMAL_CYCLIC,
        "checks": {"steady_state_rated_20c_hot_spot_c": float(h), "steady_state_rated_20c_top_oil_c": float(o),
                   "dynamic_settles_to_c": float(hd[-1]), "ageing_rate_at_98c": float(th.relative_ageing(98.0)),
                   "ageing_rate_at_104c": float(th.relative_ageing(104.0))},
        "hosting_capacity_ev": cap,
        "case": {"n_ev": CASE_EV, "season": "winter",
                 **{name: {"K_max": round(d["K_max"], 3), "hot_spot_max_c": round(d["hot_spot_max"], 1),
                           "top_oil_max_c": round(d["top_oil_max"], 1),
                           "loss_of_life_days": round(d["loss_of_life_days"], 4),
                           "within_normal_cyclic": d["within_normal_cyclic"]} for name, d in cases.items()}},
        "sweep_points": len(rows),
    }
    unc = summary["case"]["uncontrolled"]["loss_of_life_days"]
    shf = summary["case"]["shifted charging"]["loss_of_life_days"]
    summary["case"]["ageing_reduction_shifted_pct"] = round(100 * (1 - shf / unc), 1) if unc else None
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    lines = ["# Results report", "", summary["provenance"], "",
             f"Rated load at 20 °C: top oil {o:.1f} °C, hot spot {h:.1f} °C (dynamic model settles at {hd[-1]:.2f} °C).", "",
             "## EV hosting capacity (normal cyclic limits: 120 °C hot spot, 105 °C top oil, 1.5 pu)", "",
             "| Charging | Winter | Summer |", "|---|---|---|"]
    fmt = lambda c: f"{c['ev']} ({c['limited_by']})" if c["limited_by"] != "sweep end" else "200+ (end of sweep)"
    lines += [f"| {m} | {fmt(cap['winter'][m])} | {fmt(cap['summer'][m])} |" for m in study.MODES]
    lines += ["", f"## Winter day with {CASE_EV} EVs", "", "| Charging | Peak load (pu) | Peak hot spot (°C) | Life used (days) | Within limits |",
              "|---|---|---|---|---|"]
    lines += [f"| {m} | {v['K_max']} | {v['hot_spot_max_c']} | {v['loss_of_life_days']} | {v['within_normal_cyclic']} |"
              for m, v in summary["case"].items() if isinstance(v, dict)]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n")
    manifest = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "python": platform.python_version(),
                "results": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(OUT.iterdir()) if p.name != "manifest.json"}}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: summary[k] for k in ("checks", "hosting_capacity_ev", "case")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
