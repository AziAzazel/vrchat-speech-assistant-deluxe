"""Preserve installed dependency license texts and source/project references."""
from importlib.metadata import distributions
from pathlib import Path


def write_notices(target):
    sections = ["VRChat Speech Assistant Deluxe — third-party notices\n"
                "App source/build instructions: https://github.com/AziAzazel/vrchat-speech-assistant-deluxe\n"
                "Dependencies retain their respective licenses.\n"]
    for distribution in sorted(distributions(), key=lambda item: item.metadata.get("Name", "").lower()):
        metadata = distribution.metadata
        section = [f"\n{'=' * 72}\n{metadata.get('Name')} {distribution.version}\n"]
        for field in ("License-Expression", "License", "Home-page", "Project-URL"):
            for value in metadata.get_all(field, []):
                section.append(f"{field}: {value}\n")
        for file in distribution.files or []:
            if any(part.lower() in ("licenses", "license") for part in file.parts) or file.name.lower().startswith(("license", "copying")):
                source = Path(distribution.locate_file(file))
                if source.is_file():
                    try:
                        section.append(f"\n--- {file} ---\n{source.read_text(encoding='utf-8', errors='replace')}\n")
                    except OSError:
                        continue
        sections.append("".join(section))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(sections), encoding="utf-8")
