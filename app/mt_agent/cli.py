from .config import ROOT, cfg
from .planner import create
from .renderer import render
from .editor import propose_highlight
from pathlib import Path
import argparse
import time


def scan():
    for path in (ROOT / "inbox").iterdir():
        if path.is_file() and path.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi", ".webm"}:
            try:
                output = create(path)
                if output:
                    print(output)
            except Exception as error:
                print(f"ERROR {path}: {error}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init", "scan", "watch", "render", "propose-highlight"])
    parser.add_argument("plan", nargs="?")
    parser.add_argument("--count", type=int, default=12)
    args = parser.parse_args()
    if args.command == "init":
        from . import db
        db.connect().close()
    elif args.command == "scan":
        scan()
    elif args.command == "watch":
        while True:
            scan()
            time.sleep(cfg()["poll_seconds"])
    elif args.command == "render":
        if not args.plan:
            parser.error("render exige un plan JSON")
        render(args.plan)
    else:
        if not args.plan:
            parser.error("propose-highlight exige un plan JSON")
        print(propose_highlight(args.plan, args.count))


if __name__ == "__main__":
    main()
