#!/usr/bin/env python3
"""generate_leaderboard.py — rebuild leaderboard.html from the sweep_*_leaderboard.json files.

Merges base (sweep_leaderboard.json), advanced 17-task
(sweep_advanced_leaderboard.json) and stress-test 4-criteria
(sweep_stress_leaderboard.json) results, keyed by label (latest timestamp
wins). Only labels currently present in sweep_small_models.TIERS are shown
(stale/removed roster slots are excluded, same rule as before).

Speed (t/s) has no stored source anywhere in the JSON files - it was
computed live from server logs during the 2026-07-21 session, and those
logs get overwritten by every subsequent run. speed_lookup.json persists
that otherwise-unrecoverable data; rows without a known speed show "-".
Update speed_lookup.json by hand (or from a future generator that captures
it live) when a fresh measurement becomes available.
"""
import json
import re
from pathlib import Path

import sweep_small_models as ssm

REPO = ssm.REPO
SPEED_LOOKUP = REPO / "speed_lookup.json"
OUT = REPO / "leaderboard.html"


def latest_by_label(entries: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for e in entries:
        lbl = e.get("label")
        if not lbl:
            continue
        ts = e.get("timestamp", "")
        if lbl not in out or ts > out[lbl].get("timestamp", ""):
            out[lbl] = e
    return out


def load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def active_labels() -> set[str]:
    labels = set()
    for tier in ssm.TIERS.values():
        for lab, *_ in tier:
            labels.add(lab)
    return labels


def stress_summary(e: dict) -> tuple[int, int]:
    keys = ("concurrency", "self_correction", "tool_calling", "kv_cache")
    passed = sum(1 for k in keys if e.get(k, {}).get("passed"))
    return passed, len(keys)


def ratio(num, den) -> float:
    return (num / den) if (num is not None and den) else -1


def main():
    base = latest_by_label(load_json(REPO / "sweep_leaderboard.json"))
    adv = latest_by_label(load_json(REPO / "sweep_advanced_leaderboard.json"))
    stress = latest_by_label(load_json(REPO / "sweep_stress_leaderboard.json"))
    speed_lookup: dict[str, str] = json.loads(SPEED_LOOKUP.read_text(encoding="utf-8")) if SPEED_LOOKUP.exists() else {}

    active = active_labels()
    rows = []
    for lbl, e in base.items():
        if lbl not in active:
            continue
        score = e.get("passed_of_51")
        total = e.get("total")
        if score is None:
            score = e.get("passed")
        status = e.get("status")
        if status and status != "ok":
            score_str = status.replace("_", " ").upper()
        else:
            score_str = f"{score}/{total}" if total else "-"
        valid = bool(e.get("valid"))
        css = "row-valid" if valid and total == 51 else ("row-fail" if status != "ok" else "row-partial")

        exec_status = e.get("exec_trace_status")
        exec_p, exec_t = e.get("exec_trace_passed"), e.get("exec_trace_total")
        exec_str = f"{exec_p}/{exec_t}" if exec_status == "ok" else "-"
        exec_sort = ratio(exec_p, exec_t) if exec_status == "ok" else -1

        a = adv.get(lbl)
        adv_ok = a and a.get("status") == "ok"
        adv_str = f"{a.get('score')}/{a.get('total')}" if adv_ok else "-"
        adv_sort = ratio(a.get("score"), a.get("total")) if adv_ok else -1

        s = stress.get(lbl)
        if s:
            sp, st = stress_summary(s)
            stress_str = f"{sp}/{st}"
            stress_sort = ratio(sp, st)
        else:
            stress_str = "-"
            stress_sort = -1

        rows.append({
            "label": lbl,
            "css": css,
            "score": score_str,
            "score_sort": (score / total) if (score is not None and total) else -1,
            "load": round(e["load_time"], 2) if isinstance(e.get("load_time"), (int, float)) else "-",
            "bench": round(e["bench_time"], 2) if isinstance(e.get("bench_time"), (int, float)) else "-",
            "speed": speed_lookup.get(lbl, "-"),
            "exec_trace": exec_str,
            "exec_trace_sort": exec_sort,
            "advanced": adv_str,
            "advanced_sort": adv_sort,
            "stress": stress_str,
            "stress_sort": stress_sort,
            "runtime": e.get("runtime", "-"),
            "date": e.get("timestamp", "-")[:10],
        })

    def speed_key(r):
        try:
            return float(r["speed"])
        except (TypeError, ValueError):
            return -1
    rows.sort(key=speed_key, reverse=True)

    trs = []
    for r in rows:
        trs.append(
            f'<tr class="{r["css"]}">'
            f'<td>{r["label"]}</td>'
            f'<td data-sort="{r["score_sort"]}">{r["score"]}</td>'
            f'<td data-sort="{r["load"]}">{r["load"]}</td>'
            f'<td data-sort="{r["bench"]}">{r["bench"]}</td>'
            f'<td data-sort="{speed_key(r)}">{r["speed"]}</td>'
            f'<td data-sort="{r["exec_trace_sort"]}">{r["exec_trace"]}</td>'
            f'<td data-sort="{r["advanced_sort"]}">{r["advanced"]}</td>'
            f'<td data-sort="{r["stress_sort"]}">{r["stress"]}</td>'
            f'<td>{r["runtime"]}</td>'
            f'<td>{r["date"]}</td>'
            f'</tr>'
        )

    html = HTML_TEMPLATE.format(rows="".join(trs), n=len(rows))
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({len(rows)} rows)")


HTML_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Leaderboard Completa</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;margin:2em;background:#f9fafb}}
h1{{color:#1f2937}}p{{color:#6b7280}}
table{{width:100%;border-collapse:collapse;background:white;box-shadow:0 1px 3px rgba(0,0,0,0.1)}}
th,td{{padding:0.7em 1em;text-align:left;border-bottom:1px solid #e5e7eb;font-size:0.92em}}
th{{background:#374151;color:white;font-weight:600;position:sticky;top:0;cursor:pointer;user-select:none}}
th:hover{{background:#4b5563}}
th.sorted-asc::after{{content:" \\25B2"}}
th.sorted-desc::after{{content:" \\25BC"}}
tr:hover{{background:#f3f4f6}}
.row-valid td:nth-child(2){{font-weight:600;color:#059669}}
.row-partial td:nth-child(2){{color:#d97706}}
.row-fail{{opacity:0.6}}
td:nth-child(5){{color:#dc2626;font-weight:600}}
.legend{{display:flex;gap:1.5em;margin:1em 0;font-size:0.85em}}
.legend span{{display:flex;align-items:center;gap:0.4em}}
.dot{{width:10px;height:10px;border-radius:50%;display:inline-block}}
.dot-valid{{background:#059669}}.dot-partial{{background:#d97706}}.dot-fail{{background:#dc2626}}
</style></head><body>
<h1>&#127942; ik_llama.cpp Leaderboard &mdash; Completa</h1>
<p>{n} modelli attivi nel roster (tier 0-7 di <code>sweep_small_models.py</code>). Colonne cliccabili per ordinare. <strong>Speed(t/s)</strong> proviene da <code>speed_lookup.json</code> (misurazioni storiche non ricostruibili dai log server, sovrascritti ad ogni run) &mdash; "-" = mai misurato. <strong>exec-trace</strong>/<strong>Advanced</strong>/<strong>Stress</strong> "-" = mai eseguito su quel modello, non un fallimento.</p>
<div class="legend">
<span><span class="dot dot-valid"></span>51/51 validato</span>
<span><span class="dot dot-partial"></span>parziale/sotto soglia</span>
<span><span class="dot dot-fail"></span>caricamento fallito</span>
</div>
<table id="lb">
<thead><tr>
<th data-col="0" data-type="text">Modello</th>
<th data-col="1" data-type="num">Score</th>
<th data-col="2" data-type="num">Load(s)</th>
<th data-col="3" data-type="num">Bench(s)</th>
<th data-col="4" data-type="num">Speed(t/s)</th>
<th data-col="5" data-type="num">exec-trace</th>
<th data-col="6" data-type="num">Advanced(17)</th>
<th data-col="7" data-type="num">Stress(4)</th>
<th data-col="8" data-type="text">Runtime</th>
<th data-col="9" data-type="text">Ultimo test</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
<script>
(function() {{
  const table = document.getElementById('lb');
  const tbody = table.tBodies[0];
  const headers = table.querySelectorAll('th');
  let sortState = {{col: null, dir: 1}};

  function cellValue(tr, col, type) {{
    const td = tr.children[col];
    if (type === 'num') {{
      const raw = td.getAttribute('data-sort');
      const v = raw !== null ? parseFloat(raw) : parseFloat(td.textContent);
      return isNaN(v) ? -Infinity : v;
    }}
    return td.textContent.trim().toLowerCase();
  }}

  headers.forEach((th, idx) => {{
    th.addEventListener('click', () => {{
      const type = th.getAttribute('data-type');
      const dir = (sortState.col === idx) ? -sortState.dir : 1;
      sortState = {{col: idx, dir: dir}};
      headers.forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
      th.classList.add(dir === 1 ? 'sorted-asc' : 'sorted-desc');

      const rows = Array.from(tbody.querySelectorAll('tr'));
      rows.sort((a, b) => {{
        const va = cellValue(a, idx, type);
        const vb = cellValue(b, idx, type);
        if (va < vb) return -1 * dir;
        if (va > vb) return 1 * dir;
        return 0;
      }});
      rows.forEach(r => tbody.appendChild(r));
    }});
  }});
}})();
</script>
</body></html>"""


if __name__ == "__main__":
    main()
