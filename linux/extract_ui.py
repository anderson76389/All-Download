"""Extract the Windows HTML without importing or running its Windows-only code."""
import argparse
import ast
from pathlib import Path


def extract(source: Path) -> str:
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "HTML_PAGE" for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if not isinstance(value, str) or not value.lstrip().startswith("<!DOCTYPE html>"):
                raise ValueError("The Windows HTML_PAGE is no longer a literal HTML document.")
            for required in ("pywebviewready", "start_downloads", "extract_info", "save_app_settings"):
                if required not in value:
                    raise ValueError("The Windows UI has changed its JS bridge.")
            return value
    raise ValueError("The Windows source does not declare a literal HTML_PAGE.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "yt_app.py")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("ui.html"))
    args = parser.parse_args()
    html = extract(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Windows UI extracted: {len(html)} characters")


if __name__ == "__main__":
    main()
