#!/usr/bin/env python3
"""Build the interactive capacity simulator HTML from a model.json.

Usage:
  python3 build_simulator.py model.json out.html               # body-only page (for Artifact publish)
  python3 build_simulator.py model.json out.html --standalone  # full HTML file to open in any browser
Standard library only.
"""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "templates", "simulator.html")


def main(argv):
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    with open(argv[0]) as f:
        model = json.load(f)
    with open(TEMPLATE) as f:
        page = f.read()
    # "</" must not appear inside the JSON <script> block.
    data = json.dumps(model, indent=1).replace("</", "<\\/")
    title = html.escape(model.get("title", "Capacity Simulator"))
    page = page.replace("__MODEL_JSON__", data).replace("__TITLE__", title)
    if "--standalone" in argv:
        page = (
            '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            "</head>\n<body>\n" + page + "\n</body>\n</html>\n"
        )
    with open(argv[1], "w") as f:
        f.write(page)
    print(f"wrote {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
