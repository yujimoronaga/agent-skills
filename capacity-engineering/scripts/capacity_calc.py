#!/usr/bin/env python3
"""Compute utilization, headroom and break points from a capacity model.json.

Usage: python3 capacity_calc.py model.json   (prints a Markdown table; exit 1 if any scenario hits >=100%)
Format: see references/capacity-model.md. Standard library only.
This mirrors the maths in templates/simulator.html; keep the two in sync.
"""
import ast
import json
import math
import re
import sys

OK, RISK = 0.70, 1.00
FUNCS = {"min": min, "max": max, "ceil": math.ceil, "floor": math.floor, "round": round}
BUILTINS = ("fanout", "duration_s", "timeout_s", "rps", "concurrency")


def slug(name):
    s = re.sub(r"\W+", "_", name).strip("_").lower() or "c"
    return "c_" + s if s[0].isdigit() else s


class Model:
    def __init__(self, data):
        self.d = data
        self.comps = data["components"]
        for c in self.comps:
            c.setdefault("id", slug(c["name"]))
        self.by_id = {c["id"]: c for c in self.comps}
        self.by_any = {**{c["name"]: c for c in self.comps}, **self.by_id}
        self.globals = {k: (v["value"] if isinstance(v, dict) else v) for k, v in data.get("globals", {}).items()}

    # ---- expressions: numbers, variables, comp_id.variable, + - * /, min max ceil floor round ----
    def eval(self, expr, comp, load, stack=()):
        if expr is None:
            return 0.0
        if isinstance(expr, (int, float)):
            return float(expr)
        return self._ev(ast.parse(str(expr), mode="eval").body, comp, load, stack)

    def _ev(self, n, comp, load, stack):
        ev = lambda x: self._ev(x, comp, load, stack)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, ast.Div):
                return a / b if b else 0.0
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else ev(n.operand)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS:
            return float(FUNCS[n.func.id](*[ev(a) for a in n.args]))
        if isinstance(n, ast.Name):
            return self.lookup(comp, n.id, load, stack)
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            other = self.by_id.get(n.value.id)
            if not other:
                raise ValueError(f"unknown component id {n.value.id!r}")
            return self.lookup(other, n.attr, load, stack)
        raise ValueError(f"unsupported expression: {ast.dump(n)}")

    def lookup(self, comp, key, load, stack):
        if key == "load":
            return float(load)
        if comp is not None:
            if key in BUILTINS:
                v = self.builtin(comp, key, load, stack)
                return 0.0 if v is None else v
            p = comp.get("params", {}).get(key)
            if p is not None:
                return float(p["value"] if isinstance(p, dict) else p)
        if key in self.globals:
            return float(self.globals[key])
        raise ValueError(f"unknown variable {key!r} in {comp['name'] if comp else 'globals'}")

    def builtin(self, comp, key, load, stack=()):
        tag = (comp["id"], key)
        if tag in stack:
            raise ValueError(f"circular reference: {comp['id']}.{key}")
        stack = stack + (tag,)
        if key == "rps":
            return load * self.builtin(comp, "fanout", load, stack)
        if key == "concurrency":
            return self.builtin(comp, "rps", load, stack) * self.builtin(comp, "duration_s", load, stack)
        v = comp.get(key, {"fanout": 1, "duration_s": 0}.get(key))
        return None if v is None else self.eval(v, comp, load, stack)

    # ---- limits ----
    def default_demand(self, lim, comp, load):
        t = lim["type"]
        if t == "rps":
            return self.builtin(comp, "rps", load)
        if t == "concurrency":
            return self.builtin(comp, "concurrency", load)
        if t == "connections":
            holder = self.by_any.get(lim.get("held_by"))
            return self.builtin(holder or comp, "concurrency", load) * (lim.get("per_holder", 1) if holder else 1)
        if t == "throughput":
            return self.builtin(comp, "rps", load) * lim.get("unit_size", 1)
        raise ValueError(f"unknown limit type {t!r}")

    def evaluate(self, load):
        """Return {key: row} at this load. Shared limits collapse into one row; limits <= 0 are off."""
        rows, members = {}, {}
        for c in self.comps:
            for i, lim in enumerate(c.get("limits", [])):
                value = lim["per_unit"] * lim.get("units", 1) if "per_unit" in lim else self.eval(lim.get("value"), c, load)
                sid = lim.get("shared_id")
                key = "shared:" + sid if sid else f"{c['id']}:{i}"
                demand = self.eval(lim["demand"], c, load) if "demand" in lim else self.default_demand(lim, c, load)
                if key in rows:
                    rows[key]["demand"] += demand
                    members[key].append(c["name"])
                    continue
                if value <= 0:
                    continue
                rows[key] = {"comp": c["name"], "limit": lim, "value": value,
                             "base": self.eval(lim.get("baseline", 0), c, load), "demand": demand}
                members[key] = [c["name"]]
        for k, r in rows.items():
            r["comp"] = " + ".join(members[k])
            r["util"] = (r["demand"] + r["base"]) / r["value"]
        return rows

    def break_point(self, key):
        util = lambda L: self.evaluate(L).get(key, {"util": 0})["util"]
        if util(0) >= 1:
            return 0.0
        lo, hi = 0.0, 1.0
        while util(hi) < 1:
            lo, hi = hi, hi * 4
            if hi > 1e9:
                return math.inf
        for _ in range(50):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if util(mid) < 1 else (lo, mid)
        return hi

    def checks(self, load):
        """Rule checks: formula must stay within min/max at this load."""
        out = []
        for ch in self.d.get("checks", []):
            try:
                v, err = self.eval(ch["expr"], None, load), ""
            except Exception as e:  # report bad formulas instead of crashing
                v, err = float("nan"), str(e)
            ok = not err and (ch.get("max") is None or v <= ch["max"]) and (ch.get("min") is None or v >= ch["min"])
            out.append((ch, v, ok, err))
        return out

    def edges(self):
        if any("connects_to" in c for c in self.comps):
            return [(c, self.by_any[t]) for c in self.comps for t in c.get("connects_to", []) if t in self.by_any]
        return list(zip(self.comps, self.comps[1:]))

    def warnings(self):
        out = []
        for up, dn in self.edges():
            tu, td = self.builtin(up, "timeout_s", 0), self.builtin(dn, "timeout_s", 0)
            if not dn.get("async") and tu is not None and td is not None and td >= tu:
                out.append(f"timeout mismatch: {dn['name']} ({td:g}s) >= caller {up['name']} ({tu:g}s) — caller gives up while work continues")
        for c in self.comps:
            t, d = self.builtin(c, "timeout_s", 0), self.builtin(c, "duration_s", 0)
            if t is not None and d > 0.5 * t:
                out.append(f"{c['name']}: duration {d:g}s is >50% of its timeout {t:g}s")
            for lim in c.get("limits", []):
                if not lim.get("verified"):
                    out.append(f"UNVERIFIED limit: {c['name']} / {lim['name']}")
        return out


def status(u):
    return "OK" if u < OK else "RISK" if u < RISK else "FAIL"


def fmt(x):
    return "∞" if x == math.inf else f"{x:,.0f}" if x >= 10 else f"{x:,.2f}"


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    with open(argv[0]) as f:
        m = Model(json.load(f))
    scns = m.d["scenarios"]
    at = {s: m.evaluate(L) for s, L in scns.items()}
    keys = list(dict.fromkeys(k for s in scns for k in at[s]))
    brk = {k: m.break_point(k) for k in keys}
    keys.sort(key=lambda k: brk[k])
    row = lambda k: next(at[s][k] for s in scns if k in at[s])

    unit = m.d.get("load_unit", "req/s")
    head = ["#", "Component", "Limit", "Value", "Verified", f"Breaks at {unit}"] + [f"{s} ({fmt(L)}/s)" for s, L in scns.items()]
    print("| " + " | ".join(head) + " |")
    print("|" + "|".join("---" for _ in head) + "|")
    for i, k in enumerate(keys, 1):
        r = row(k)
        cells = [str(i), r["comp"], r["limit"]["name"], fmt(r["value"]), "yes" if r["limit"].get("verified") else "NO", fmt(brk[k])]
        cells += [f"{at[s][k]['util']*100:.0f}% {status(at[s][k]['util'])}" if k in at[s] else "–" for s in scns]
        print("| " + " | ".join(cells) + " |")
    failing_any = False
    if keys:
        r = row(keys[0])
        print(f"\nFIRST TO BREAK: {r['comp']} — {r['limit']['name']} at ~{fmt(brk[keys[0]])} {unit} ({r['limit'].get('failure') or 'failure mode not set'})")
        for s in scns:
            fails = [at[s][k]["comp"] for k in keys if k in at[s] and at[s][k]["util"] >= RISK]
            risky = [k for k in keys if k in at[s] and OK <= at[s][k]["util"] < RISK]
            failing_any |= bool(fails)
            print(f"  {s}: {len(fails)} FAIL, {len(risky)} RISK" + (f" — fails: {', '.join(fails)}" if fails else ""))
    if m.d.get("checks"):
        print("\nRULE CHECKS")
        for s_name, L in scns.items():
            for ch, v, ok, err in m.checks(L):
                failing_any |= not ok
                cond = " and ".join(x for x in (f">= {ch['min']:g}" if ch.get("min") is not None else "", f"<= {ch['max']:g}" if ch.get("max") is not None else "") if x)
                print(f"  {s_name}: {'PASS' if ok else 'FAIL'} — {ch['name']}: {err or fmt(v)} {ch.get('unit', '')} (must be {cond})")
    w = m.warnings()
    if w:
        print("\nWARNINGS")
        for x in w:
            print(f"  - {x}")
    return 1 if failing_any else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
