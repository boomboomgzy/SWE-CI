import sqlite3
import json
from pathlib import Path
from datetime import datetime


DB_DIR = Path("/data/SWE-CI/experiments/example/15r10nk__inline-snapshot__3bb05d__e2b9b2/db")


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ts(ms: int | None) -> str:
    if ms is None:
        return "N/A"
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def view_parts(db_path: str | Path) -> None:
    """Print every part with direction: [CLIENT] for user/tool-result, [LLM] for assistant output."""
    with _connect(db_path) as conn:
        role_map = {
            r["id"]: json.loads(r["data"]).get("role", "?")
            for r in conn.execute("SELECT id, data FROM message").fetchall()
        }
        rows = conn.execute(
            "SELECT id, message_id, time_created, data FROM part ORDER BY time_created"
        ).fetchall()

    for i, r in enumerate(rows, 1):
        data = json.loads(r["data"])
        ptype = data.get("type", "?")

        if ptype == "step-start":
            print(f"\n[LLM]    part={i}  type=step-start  @ {_ts(r['time_created'])}")
            continue

        if ptype == "step-finish":
            tokens = data.get("tokens", {})
            print(f"\n[LLM]    part={i}  type=step-finish  reason={data.get('reason')}  in={tokens.get('input',0)} out={tokens.get('output',0)}")
            continue

        role = role_map.get(r["message_id"], "?")

        if ptype == "text":
            direction = "CLIENT" if role == "user" else "LLM"
            text = data.get("text", "").strip()
            if not text:
                continue
            print(f"\n[{direction}] part={i}  type=text  @ {_ts(r['time_created'])}")
            print(text[:300])

        elif ptype == "tool":
            state = data.get("state", {})
            inp = json.dumps(state.get("input", {}), ensure_ascii=False)
            out = str(state.get("output", "")).strip()
            # tool call: LLM decided to call it; tool result: client executed and returned it
            print(f"\n[LLM]    part={i}  type=tool-call  tool={data.get('tool')}  @ {_ts(r['time_created'])}")
            print(f"  input={inp[:200]}")
            if out:
                print(f"\n[CLIENT] part={i}  type=tool-result  tool={data.get('tool')}")
                print(f"  output={out[:300]}")

        else:
            direction = "CLIENT" if role == "user" else "LLM"
            print(f"\n[{direction}] part={i}  type={ptype}  @ {_ts(r['time_created'])}")
            print(str(data)[:200])


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python check.py <db_name_or_path>")
        print("\nAvailable DBs:")
        for db in sorted(DB_DIR.glob("*.db")):
            print(f"  {db.name}")
        sys.exit(0)

    arg = sys.argv[1]
    db_path = Path(arg) if Path(arg).exists() else DB_DIR / arg
    view_parts(db_path)
