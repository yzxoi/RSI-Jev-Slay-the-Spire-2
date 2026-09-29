"""Fixed-cohort identity/schema audit, not an engine replay or policy evaluation."""
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
UP = ROOT / "vendor/sts2core-audit"
META = "b7de162"
UP_SHA = "3b2d969d025b9e64bc96b9a15928bd2a0d824bf2"


def historical(path):
    return json.loads(subprocess.check_output(["git", "show", f"{META}:{path}"], cwd=ROOT))


def resolve_trace(exp, relative):
    candidates = [ROOT / relative]
    candidates += [p / relative for p in sorted(ROOT.parent.joinpath(ROOT.name + "-worktrees").glob(f"*-{exp.lower()}*"))]
    return next((p for p in candidates if p.is_file()), None)


def clean_id(obj, fields, status=False):
    for f in fields:
        if obj.get(f):
            value = str(obj[f]).split(".")[-1]
            return value
    value = re.sub(r"[^A-Za-z0-9]+", "_", obj.get("name", "")).strip("_").upper()
    if status and value and not value.endswith("_POWER"):
        value += "_POWER"
    return value or obj.get("name", "")


def shape(s):
    native = "screen" in s
    c = (s.get("combat") or {}) if native else s
    p = (c.get("player") or {}) if native else s.get("player", {})
    run = (s.get("run") or {}) if native else p
    hand = c.get("hand") or []
    enemies = c.get("enemies") or []
    powers = p.get("powers", []) if native else s.get("player_powers", [])
    powers = list(powers or []) + [z for e in enemies for z in (e.get("powers") or [])]
    return {
        "combat": bool(c) and (s.get("in_combat", False) or s.get("screen") == "COMBAT" or s.get("decision") == "combat_play"),
        "character": run.get("character_id", p.get("name", "")),
        "floor": run.get("floor", s.get("context", {}).get("floor")),
        "turn": s.get("turn", s.get("round")),
        "hp": p.get("current_hp", p.get("hp")),
        "hand": hand, "deck": run.get("deck") or [], "enemies": enemies,
        "potions": [x for x in run.get("potions", []) or [] if x.get("occupied", True) and (x.get("name") or x.get("potion_id"))],
        "relics": run.get("relics") or [], "statuses": powers,
        "pending": bool(s.get("selection")) or s.get("decision") in ("card_select", "hand_select"),
        "has_draw_contents": isinstance(c.get("draw_pile"), list) or isinstance(c.get("draw_pile_order"), list),
        "has_discard_contents": isinstance(c.get("discard_pile"), list),
        "has_exhaust_contents": isinstance(c.get("exhaust_pile"), list),
        "orbs": bool(p.get("orbs")), "pets": bool(p.get("pets")), "stars": bool(p.get("stars")),
        "coop": len(c.get("players") or []) > 1 or (s.get("session") or {}).get("mode") == "multiplayer",
        "hand_affliction": any(x.get("affliction") or x.get("affliction_id") for x in hand),
    }


def main():
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=UP, text=True).strip() == UP_SHA
    cards = json.loads((UP / "traces/cards_catalog.json").read_text())["cards"]
    # The discovered-card snapshot can lag implemented cards. Bridge exact constant
    # names to the actual compiled table; do not guess cross-character aliases.
    catalog_lines = subprocess.check_output([str(ROOT / "artifacts/private/e114-probe"), "--catalog"], text=True)
    compiled_names = {int(i): name for i, name in (line.split("\t") for line in catalog_lines.splitlines())}
    content_source = (UP / "src/content.rs").read_text().split("pub mod card {", 1)[1].split("\n}", 1)[0]
    constant_names = {key: compiled_names[int(i)] for key, i in re.findall(r"pub const (\w+): u16 = (\d+);", content_source) if int(i) in compiled_names}
    enemy_table = json.loads((UP / "data/enemy_ids.json").read_text())["monsters"]
    enemy_names = {v["key"]: v.get("kernel_enemy") for v in enemy_table.values()}
    evidence, samples, action_potions = [], [], []

    def load(exp, label, path, expected):
        p = resolve_trace(exp, path)
        entry = {"cohort": exp, "label": label, "trace_path": path, "expected_sha256": expected, "available": p is not None}
        evidence.append(entry)
        if p is None:
            return []
        raw = p.read_bytes()
        entry.update(sha256=hashlib.sha256(raw).hexdigest())
        entry["hash_matches"] = entry["sha256"] == expected
        if not entry["hash_matches"]:
            raise ValueError(f"trace hash mismatch: {exp} {label}")
        return [json.loads(l) for l in raw.splitlines() if l.strip()]

    fixtures = historical("experiments/E113/fixtures.json")
    for case in fixtures["cases"]:
        src = case["source"]
        load("E113", case["id"], src["trace_path"], src["trace_sha256"])
        st = case["combat"]["entry"]
        samples.append({"cohort": "E113", "label": case["id"], "seq": "frozen_entry", "state": shape(st)})

    for exp, entries in [
        ("E092", [historical(f"experiments/E092/segment{i:02d}-summary.json") for i in range(1, 72)]),
        ("E102", historical("experiments/E102/result.json")["results"]),
    ]:
        for i, entry in enumerate(entries):
            label = str(entry.get("segment", f"{entry.get('case')}-{entry.get('arm')}"))
            rows = load(exp, label, entry["trace_path"], entry["trace_sha256"])
            current = None
            for r in rows:
                d = r.get("data", {})
                if r.get("kind") == "before":
                    current = shape(d["state"])
                    samples.append({"cohort": exp, "label": label, "seq": r["seq"], "state": current})
                if r.get("kind") == "selected" and current:
                    choice = d.get("choice", d)
                    a = choice.get("action", {})
                    if a.get("action") == "use_potion":
                        idx = (a.get("args") or {}).get("potion_index", a.get("potion_index", a.get("option_index", a.get("slot_index"))))
                        candidates = current["potions"]
                        selected = next((p for p in candidates if p.get("index") == idx), {})
                        action_potions.append({"cohort": exp, "label": label, "seq": r["seq"], "floor": current["floor"], "turn": current["turn"], "hp": current["hp"], "index": idx, "potion_id": clean_id(selected, ["potion_id", "id"]), "name": selected.get("name"), "source": d.get("source", "native_controller")})

    co = historical("experiments/E110/result.json")
    co_summary = ROOT / "artifacts/runs/E110/segment01.json"
    if co_summary.is_file():
        cm = json.loads(co_summary.read_text())
        cm = cm.get("result", cm)
        path = cm.get("trace_path") or f"artifacts/runs/{cm['run_id']}/decisions.jsonl"
        rows = load("E110", "segment01", path, co["trace_sha256"])
        for r in rows:
            if r.get("kind") == "before":
                samples.append({"cohort": "E110", "label": "segment01", "seq": r["seq"], "state": shape(r["data"]["state"])})
    else:
        evidence.append({"cohort": "E110", "available": False, "reason": "missing segment summary"})

    queries = set()
    def identity(kind, obj):
        if kind == "card":
            key = clean_id(obj, ["card_id", "id"])
            name = cards.get(key, {}).get("name") or constant_names.get(key) or obj.get("name", "")
        elif kind == "enemy":
            key = clean_id(obj, ["enemy_id", "id"])
            name = enemy_names.get(key) or obj.get("name", "")
        else:
            key = clean_id(obj, [kind + "_id", "power_id" if kind == "status" else "id", "id"], status=kind == "status")
            name = key
        name = name.replace("\t", " ").replace("\n", " ")
        queries.add((kind, name))
        return key, name

    for item in samples:
        st = item["state"]
        item["identities"] = {kind: [identity(kind, x) for x in st[field]] for field, kind in [("hand", "card"), ("deck", "card"), ("enemies", "enemy"), ("potions", "potion"), ("relics", "relic"), ("statuses", "status")] if field != "hand"}
        item["hand_queries"] = [identity("card", x) for x in st["hand"]]
    for p in action_potions:
        queries.add(("potion", p["potion_id"]))
    data = "".join(f"{k}\t{v}\n" for k, v in sorted(queries))
    output = subprocess.check_output([str(ROOT / "artifacts/private/e114-probe")], input=data, text=True)
    lookup = {}
    for line in output.splitlines():
        kind, query, status, label = line.split("\t")
        lookup[(kind, query)] = {"status": status, "label": label}
    for p in action_potions:
        p["upstream"] = lookup[("potion", p["potion_id"])]
    groups = {}
    per_case = []
    for cohort in ["E113", "E092", "E102", "E110"]:
        ss = [s for s in samples if s["cohort"] == cohort]
        counts = collections.Counter()
        objects = {k: {} for k in ("card", "enemy", "potion", "relic", "status")}
        for item in ss:
            st = item["state"]
            counts["observations"] += 1
            counts["combat_observations"] += st["combat"]
            for f in ("pending", "has_draw_contents", "has_discard_contents", "has_exhaust_contents", "orbs", "pets", "stars", "coop", "hand_affliction"):
                counts[f] += bool(st[f])
            for kind, vals in item["identities"].items():
                for key, query in vals:
                    objects[kind][key] = {"query": query, **lookup[(kind, query)]}
            missing_hand = [key for key, q in item["hand_queries"] if lookup[("card", q)]["status"] != "known"]
            counts["combat_all_hand_names_known"] += st["combat"] and not missing_hand
            if cohort == "E113":
                missing_deck = [key for key, q in item["identities"]["card"] if lookup[("card", q)]["status"] != "known"]
                per_case.append({"case": item["label"], "floor": st["floor"], "missing_hand": sorted(set(missing_hand)), "missing_deck": sorted(set(missing_deck)), "held_potions": sorted({key for key, q in item["identities"]["potion"]})})
        groups[cohort] = {"counts": dict(counts), "objects": objects, "distinct_status_counts": {k: dict(collections.Counter(v["status"] for v in d.values())) for k, d in objects.items()}}
    result = {
        "experiment": "E114", "audit_code_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "metadata_sha": META, "upstream_sha": UP_SHA, "scope": "identity and schema inspection only; no counterfactual battle or full state replay",
        "normalization": "Cards: exact upstream catalog ID->Chinese name, then exact Rust card constant->compiled name, otherwise observed name; no cross-character basic-card aliases. Enemies: upstream ID mapping then observed name. CLI items without IDs use uppercase underscore name; this is identity normalization, not rule verification.",
        "evidence": evidence, "cohorts": groups, "e113_cases": per_case, "actual_potion_actions": action_potions,
        "limitations": ["Not a representative win-rate sample", "Input observations may omit pile contents and persistent private counters", "Known ID/status is not proof of implemented mechanics", "CLI v0.111.0 and older native traces differ from upstream v0.107.1", "No draw order inferred from a deck list", "E110 first segment has no AI combat; co-op is a structural scope check"]}
    out = ROOT / "experiments/E114/results.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"evidence_files": len(evidence), "available": sum(x["available"] for x in evidence), "cohorts": {k: {"counts": v["counts"], "identities": v["distinct_status_counts"]} for k, v in groups.items()}, "potion_actions": len(action_potions)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
