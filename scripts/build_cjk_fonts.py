"""Rebuild renamed static CJK fonts from hash-pinned, OFL-licensed Noto release assets.

Run from the repository root: uv run --project backend python scripts/build_cjk_fonts.py
Downloads are build inputs only. Report rendering never downloads fonts.
"""

import hashlib
from pathlib import Path

import httpx
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "backend/src/ase/adapters/reports/fonts"
CACHE = ROOT / "data/cjk-font-build"
BASE = "https://raw.githubusercontent.com/notofonts/noto-cjk/Sans2.004/"
SOURCES = {
    "SC": "d68bafcb48a2707749396aa12bbbd833cb70401f3a9a689fd2902c7e0d295964",
    "TC": "ac091cc8cd19e848202afc8fe6d3809b4526c8fdbdb4be82da20c4f785949591",
}
LICENCE_HASH = "6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2"


def asset(path: str, digest: str) -> bytes:
    cached = CACHE / Path(path).name
    if cached.exists():
        content = cached.read_bytes()
    else:
        with httpx.Client(timeout=60, follow_redirects=False) as client:
            response = client.get(BASE + path)
            response.raise_for_status()
            content = response.content
        if len(content) > 25_000_000:
            raise ValueError("Unexpected font asset size")
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError("Font asset does not match its pinned upstream digest")
    cached.write_bytes(content)
    return content


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    for region, digest in SOURCES.items():
        filename = f"NotoSans{region}-VF.ttf"
        asset(f"Sans/Variable/TTF/Subset/{filename}", digest)
        font = TTFont(CACHE / filename, recalcTimestamp=False)
        instantiateVariableFont(font, {"wght": 400}, inplace=True, static=True)
        family = f"ASE Research Sans {region}"
        names = {
            1: family,
            2: "Regular",
            3: f"{family} 2.004 static400",
            4: f"{family} Regular",
            6: f"ASEResearchSans{region}-Regular",
            16: family,
            17: "Regular",
        }
        for record in font["name"].names:
            if record.nameID in names:
                record.string = names[record.nameID].encode(record.getEncoding())
        font.save(OUTPUT / f"ASEResearchSans{region}-Regular.ttf", reorderTables=True)
        font.close()
    (OUTPUT / "OFL-NotoCJK.txt").write_bytes(asset("LICENSE", LICENCE_HASH))


if __name__ == "__main__":
    main()
