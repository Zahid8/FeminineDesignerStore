"""Split 2x2 product canvases into 4 square 1080px photos.

usage: python3 split_canvas.py <canvas_dir> <out_dir>
"""
import json, re, sys
from pathlib import Path
import numpy as np
from PIL import Image

WHITE = 236  # a pixel is background if every channel is above this

def white_mask(a):
    return a.min(axis=2) > WHITE

def find_gap(frac, lo, hi, centre):
    """Best split index in [lo, hi): middle of the near-white run closest to centre."""
    best, best_d = None, None
    for thresh in (0.995, 0.98, 0.95):
        runs, start = [], None
        for i in range(lo, hi):
            if frac[i] >= thresh:
                start = i if start is None else start
            elif start is not None:
                runs.append((start, i)); start = None
        if start is not None: runs.append((start, hi))
        for s, e in runs:
            mid = (s + e) // 2; d = abs(mid - centre)
            if best is None or d < best_d: best, best_d = mid, d
        if best is not None: return best, thresh
    return centre, None

def trim(tile):
    a = np.asarray(tile); m = ~white_mask(a)
    rows = np.where(m.sum(axis=1) > 3)[0]; cols = np.where(m.sum(axis=0) > 3)[0]
    if not len(rows) or not len(cols): return tile
    return tile.crop((cols[0], rows[0], cols[-1] + 1, rows[-1] + 1))

def pad_colour(tile):
    a = np.asarray(tile).reshape(-1, 3) if False else np.asarray(tile)
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    if white_mask(border[None])[0].mean() > 0.6: return (255, 255, 255)
    return tuple(int(v) for v in np.median(border, axis=0))

def is_plain_white(tile):
    a = np.asarray(tile); border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    return np.median(border.min(axis=1)) >= 250

def square(tile, size=1080, margin=0.05):
    w, h = tile.size
    if not is_plain_white(tile):
        # Full-bleed studio photo: crop to a centred square (top-aligned if tall) instead of boxing it in.
        side = min(w, h); left = (w - side) // 2; top = 0 if h > w else (h - side) // 2
        return tile.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
    side = int(max(w, h) * (1 + 2 * margin))
    bg = Image.new("RGB", (side, side), pad_colour(tile))
    bg.paste(tile, ((side - w) // 2, (side - h) // 2))
    return bg.resize((size, size), Image.LANCZOS)

def split(path):
    img = Image.open(path).convert("RGB"); a = np.asarray(img); H, W = a.shape[:2]
    wm = white_mask(a)
    y, ty = find_gap(wm.mean(axis=1), int(H * .3), int(H * .7), H // 2)
    tiles, info = [], {"size": [W, H], "row": [int(y), ty], "cols": []}
    for top, bot in ((0, y), (y, H)):
        x, tx = find_gap(wm[top:bot].mean(axis=0), int(W * .3), int(W * .7), W // 2)
        info["cols"].append([int(x), tx])
        tiles += [img.crop((0, top, x, bot)), img.crop((x, top, W, bot))]
    return [square(trim(t)) for t in tiles], info

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

if __name__ == "__main__":
    src, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    report = {}
    for p in sorted(src.glob("*.png")):
        photos, info = split(p); d = out / slugify(p.stem); d.mkdir(exist_ok=True)
        for i, ph in enumerate(photos, 1): ph.save(d / f"{i}.jpg", quality=90, optimize=True, progressive=True)
        sheet = Image.new("RGB", (4 * 270 + 30, 270), (200, 200, 200))
        for i, ph in enumerate(photos): sheet.paste(ph.resize((270, 270)), (i * 280, 0))
        sheet.save(out / f"_sheet_{slugify(p.stem)}.jpg", quality=80)
        report[p.name] = info
    (out / "_split_report.json").write_text(json.dumps(report, indent=1))
    for k, v in report.items(): print(v["row"], v["cols"], k)
