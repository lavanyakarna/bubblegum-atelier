#!/usr/bin/env python3
"""
apply_chat_update.py — makes the Boutique Concierge smarter, and cleans up.

What it does:

  1. CONCIERGE REBUILD
       - new matching: whole meaningful words only. The old version matched the
         greeting "hi" inside "shipping", "which" and "this".
       - new knowledge: 30 intents and 214 example phrases (was 22 and 67)
       - real catalogue answers: "how much are the sugar rush heels" now replies
         with the actual price, sizes and stock from your products.json
       - category browsing: "show me bags" lists real pieces with prices
       - honest fallback: when it doesn't know, it says so and offers what it can do

  2. RETRAINS the chatbot model so the new knowledge is live

  3. CLEANS the test leftovers that earlier pytest runs wrote into your real
     boutique (the "pytest-tagger" posts on your Style Wall)

  4. STOPS it happening again: a new tests/conftest.py snapshots your data before
     the suite runs and restores it afterwards.

Run from the PROJECT ROOT (the folder with app/ and public/):

    python apply_chat_update.py --check    # show every change, modify nothing
    python apply_chat_update.py            # do it (backs up everything first)
    python apply_chat_update.py --no-clean # install, but leave data alone
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAYLOAD = HERE / "payload"
BACKUP = ".pre-chatupdate.bak"

FILES = [
    "app/services/chatbot_service.py",
    "tests/conftest.py",
    "tests/test_endpoints.py",
    "data/intents.json",
]

REQUIRED = [
    "app/main.py",
    "app/routers/stylewall.py",
]


def find_python(root: Path) -> str:
    """Use the project's virtualenv when there is one, else plain python."""
    for candidate in (".venv/Scripts/python.exe", "venv/Scripts/python.exe",
                      ".venv/bin/python", "venv/bin/python"):
        if (root / candidate).exists():
            return str(root / candidate)
    return sys.executable


def main() -> int:
    ap = argparse.ArgumentParser(description="Upgrade the concierge and tidy the test leftovers.")
    ap.add_argument("root", nargs="?", default=".", help="project root (default: current directory)")
    ap.add_argument("--check", action="store_true", help="dry run - report only")
    ap.add_argument("--no-clean", action="store_true", help="skip cleaning the test leftovers")
    ap.add_argument("--no-train", action="store_true", help="skip retraining the chatbot model")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    dry = args.check

    problems = []
    if not (root / "app").is_dir():
        problems.append("no app/ folder here")
    if not PAYLOAD.is_dir():
        problems.append(f"payload/ folder missing next to this script ({PAYLOAD})")
    for rel in REQUIRED:
        if not (root / rel).exists():
            problems.append(f"{rel} not found - this update expects the earlier ones to be installed")
    if problems:
        print("Cannot install from here:")
        for p in problems:
            print(f"  - {p}")
        print(f"\nResolved project root: {root}")
        return 2

    print(f"Project root : {root}")
    print(f"Mode         : {'DRY RUN' if dry else 'INSTALL'}\n")

    # ---------------------------------------------------------------- 1. files
    print("1. Concierge files")
    for rel in FILES:
        src, dst = PAYLOAD / rel, root / rel
        if not src.exists():
            print(f"   SKIP      {rel} (not in the update)")
            continue
        if dry:
            print(f"   WOULD COPY {rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.copy2(dst, Path(str(dst) + BACKUP))
        shutil.copy2(src, dst)
        print(f"   copied    {rel}")

    # ---------------------------------------------------------------- 2. train
    print("\n2. Retraining the concierge")
    if args.no_train:
        print("   skipped (--no-train)")
    elif dry:
        print("   WOULD RUN  python -m app.services.chatbot_service")
    else:
        python = find_python(root)
        result = subprocess.run([python, "-m", "app.services.chatbot_service"],
                                cwd=str(root), capture_output=True, text=True)
        out = (result.stdout or "").strip().splitlines()
        if result.returncode == 0 and out:
            print(f"   {out[-1]}")
        else:
            print("   Could not retrain automatically. Run this yourself:")
            print("     python -m app.services.chatbot_service")
            if result.stderr:
                print("   " + result.stderr.strip().splitlines()[-1])

    # ---------------------------------------------------------------- 3. clean
    print("\n3. Test leftovers from earlier pytest runs")
    cleaner = HERE / "clean_test_junk.py"
    if not cleaner.exists():
        cleaner = PAYLOAD / "clean_test_junk.py"
    if args.no_clean:
        print("   skipped (--no-clean)")
    elif not cleaner.exists():
        print("   clean_test_junk.py not found next to this script - skipping")
    elif dry:
        result = subprocess.run([sys.executable, str(cleaner), str(root), "--check"],
                                capture_output=True, text=True)
        for line in (result.stdout or "").strip().splitlines():
            if line.startswith("  "):
                print("  " + line)
    else:
        result = subprocess.run([sys.executable, str(cleaner), str(root)],
                                capture_output=True, text=True)
        for line in (result.stdout or "").strip().splitlines():
            if line.startswith("  ") or "Removed" in line or "Nothing to clean" in line:
                print("  " + line)

    # ---------------------------------------------------------------- done
    if not dry:
        print("\nDone. Next:")
        print("  1. pytest tests/ -v          (expect 34 passed)")
        print("  2. restart the server and open the Concierge")
        print("     try: 'how much are the sugar rush platform heels'")
        print("          'show me bags'")
        print("          'how much is shipping'")
        print("\nAnything replaced has a .pre-chatupdate.bak copy, and cleaned data has .junk-backup")
    return 0


if __name__ == "__main__":
    sys.exit(main())
