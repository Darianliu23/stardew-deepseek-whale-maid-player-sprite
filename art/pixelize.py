"""把 GPT 生成的像素风角色图转成真正的低分辨率精灵表。

用法:
  python pixelize.py 输入.png 输出.png --cols 4 --rows 3 [--height 30 | --block 10.3] [--cell 40x40] [--colors 20]

- 背景必须是纯品红 (#FF00FF)。
- 自动找出每个角色所在的格子（按行、列的空白间隔切开），要求切出来正好 cols x rows 个。
- --height：最高的那一帧缩成多少像素高；--block：原图多少像素算一个像素（不同姿态图要和走路图保持同样大小时用它）。
- 每格里角色脚底对齐格子底部，头部（上 40%）中心对齐格子中线，这样换帧时不会左右抖。
- 先在原图上压缩调色板，再给每个块取出现最多的颜色，比取平均值清楚。
"""
import argparse
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out")
ap.add_argument("--cols", type=int, required=True)
ap.add_argument("--rows", type=int, required=True)
ap.add_argument("--height", type=float, default=30)
ap.add_argument("--block", type=float, default=0)
ap.add_argument("--cell", default="32x32")
ap.add_argument("--colors", type=int, default=20)
ap.add_argument("--preview", default="")
ap.add_argument("--ref", default="", help="用第 r,c 格（从 0 数）的高度定比例：这一格缩成 --height 高")
ap.add_argument("--strip-tool", action="store_true", help="抠掉灰色工具头、棕色手柄/鱼竿、灰蓝水壶（游戏会自己画工具）")
ap.add_argument("--front", default="", help="正脸格子，取样时优先保证左右对称：'0' 是第 0 行整行，'1:3' 是第 1 行第 3 列，逗号分隔")
args = ap.parse_args()
CELL_W, CELL_H = (int(v) for v in args.cell.split("x"))

im = np.array(Image.open(args.src).convert("RGB")).astype(int)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
# 品红背景：R、B 高，G 低；边缘的混色也算背景
bg = ((np.minimum(r, b) - g) > 110) & (g < 120)
fg = ~bg
if args.strip_tool:
    lum = (r + g + b) / 3
    # 工具头的灰色比围裙阴影更"不偏蓝"（围裙阴影 b-r 约 24~36）
    grey = (abs(r - g) < 12) & (b - r >= -6) & (b - r <= 18) & (lum > 105) & (lum < 178)
    # 手柄和鱼竿的棕色；排除皮肤（更亮）和腮红（g≈b）
    brown = (r > g) & (g - b >= 10) & (r - b > 40) & (lum > 45) & (lum < 185)
    # 灰蓝色水壶：比头发不饱和得多
    can = (g - r >= 12) & (b - r >= 40) & (b - r <= 78) & (b - g >= 20) & (b - g <= 55) & (lum > 125) & (lum < 215)
    fg &= ~(grey | brown | can)

_q = Image.fromarray(np.where(fg[..., None], im, 0).astype(np.uint8)).quantize(
    colors=args.colors + 1, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
qidx = np.array(_q)
palette = np.array(_q.getpalette()[:3 * (args.colors + 1)]).reshape(-1, 3)


def runs(a, want):
    """找出连续的前景段；段数多于 want 时，反复合并间隔最小的两段。"""
    res, s = [], None
    for i, v in enumerate(a):
        if v and s is None:
            s = i
        if not v and s is not None:
            res.append([s, i - 1])
            s = None
    if s is not None:
        res.append([s, len(a) - 1])
    res = [x for x in res if x[1] - x[0] > 4]  # 丢掉噪点
    while len(res) > want:
        gaps = [res[i + 1][0] - res[i][1] for i in range(len(res) - 1)]
        i = int(np.argmin(gaps))
        res[i] = [res[i][0], res[i + 1][1]]
        del res[i + 1]
    return res


# 算范围时只看"实心"像素：不算描边（太暗），且每行/列至少 6 个，免得残留的工具描边把范围撑大
core = fg & ((r + g + b) / 3 >= 70)
row_runs = runs(core.sum(1) >= 6, args.rows)
assert len(row_runs) == args.rows, f"只切出 {len(row_runs)} 行：{row_runs}"

cells = {}
for ri, (y0, y1) in enumerate(row_runs):
    band = core[y0:y1 + 1]
    col_runs = runs(band.sum(0) >= 6, args.cols)
    assert len(col_runs) == args.cols, f"第 {ri + 1} 行只切出 {len(col_runs)} 列：{col_runs}"
    for ci, (x0, x1) in enumerate(col_runs):
        m = core[y0:y1 + 1, x0:x1 + 1]
        ys = np.where(m.sum(1) >= 6)[0]
        # 描边在实心范围外还有一圈，上下各放宽几像素再取
        x0, x1 = max(0, x0 - 4), min(fg.shape[1] - 1, x1 + 4)
        cells[ri, ci] = (max(0, y0 + ys.min() - 4), min(fg.shape[0] - 1, y0 + ys.max() + 6), x0, x1)

if args.block:
    block = args.block
elif args.ref:
    rr, rc = (int(v) for v in args.ref.split(","))
    block = (cells[rr, rc][1] - cells[rr, rc][0] + 1) / args.height
else:
    block = max(c[1] - c[0] + 1 for c in cells.values()) / args.height
print(f"block size {block:.2f}")
print("cell heights:", {k: round((v[1] - v[0] + 1) / block, 1) for k, v in cells.items()})

def is_front(ri, ci):
    """--front 指定的正脸格子："0" 表示第 0 行整行，"1:3" 表示第 1 行第 3 列。"""
    for item in filter(None, args.front.split(",")):
        r_, _, c_ = item.partition(":")
        if int(r_) == ri and (not c_ or int(c_) == ci):
            return True
    return False


def sample(cfg, bottom, head_cx, dx, dy):
    """按给定的取样起点偏移，把一格缩成 CELL_W x CELL_H。返回 (RGBA 图, 平均纯度)。"""
    out = np.zeros((CELL_H, CELL_W, 4), dtype=np.uint8)
    purity = []
    for ty in range(CELL_H):
        for tx in range(CELL_W):
            sy0 = bottom + 1 - (CELL_H - ty) * block + dy
            sx0 = head_cx + (tx - CELL_W / 2) * block + dx
            ya, yb = int(sy0 + block * 0.15), int(sy0 + block * 0.85) + 1
            xa, xb = int(sx0 + block * 0.15), int(sx0 + block * 0.85) + 1
            if ya < 0 or xa < 0 or yb > im.shape[0] or xb > im.shape[1]:
                continue
            fgb = cfg[ya:yb, xa:xb]
            if fgb.mean() < 0.5:
                continue
            counts = np.bincount(qidx[ya:yb, xa:xb][fgb])
            purity.append(counts.max() / counts.sum())
            out[ty, tx] = [*palette[counts.argmax()].astype(np.uint8), 255]
    return out, (float(np.mean(purity)) if purity else 0.0)


def symmetry(cell):
    """正脸头部（最上面 12 行）的左右对称程度：左右镜像位置颜色相同的比例，取两种对称轴里更好的。"""
    rows = np.where((cell[..., 3] > 0).any(1))[0]
    if len(rows) == 0:
        return 0.0
    head = cell[rows[0]:rows[0] + 12]
    best = 0.0
    for axis in (CELL_W / 2 - 0.5, CELL_W / 2 - 1):  # 偶数宽（两列之间）或奇数宽（某一列正中）
        same = total = 0
        for x in range(CELL_W):
            mx = int(round(2 * axis - x))
            if mx <= x or mx >= CELL_W:
                continue
            a_, b_ = head[:, x], head[:, mx]
            used = (a_[:, 3] > 0) | (b_[:, 3] > 0)
            total += used.sum()
            same += (used & (a_ == b_).all(1)).sum()
        best = max(best, same / total if total else 0.0)
    return best


sheet = np.zeros((args.rows * CELL_H, args.cols * CELL_W, 4), dtype=np.uint8)
# GPT 画的"像素"和我们的取样格子大小不一样，取样起点差半格，眼睛就可能一只 2 像素一只 1 像素。
# 所以试一圈起点：正脸看左右对称，其他看每块颜色纯不纯（线条干净）。
# 同一行是同一个方向的连续动画，整行共用一个起点，否则相邻帧会错开 1 像素、走起来抖
OFFSETS = [(fx, fy) for fx in np.arange(-0.5, 0.5, 1 / 6) for fy in (0.0, 0.25, 0.5)]
for ri in range(args.rows):
    tried = {}  # (ci, 偏移序号) -> (分数, 图)
    for ci in range(args.cols):
        top, bottom, x0, x1 = cells[ri, ci]
        own = np.zeros_like(fg)
        own[top:bottom + 1, x0:x1 + 1] = True
        cfg = fg & own
        head_bottom = top + int((bottom - top) * 0.4)
        hx = np.where(cfg[top:head_bottom + 1].any(0))[0]
        head_cx = (hx.min() + hx.max()) / 2
        front = is_front(ri, ci)
        for k, (fx, fy) in enumerate(OFFSETS):
            cand, purity = sample(cfg, bottom, head_cx, fx * block, fy * block)
            tried[ci, k] = (purity + (2.0 * symmetry(cand) if front else 0.0), cand)
    best_k = max(range(len(OFFSETS)), key=lambda k: sum(tried[ci, k][0] for ci in range(args.cols)))
    for ci in range(args.cols):
        sheet[ri * CELL_H:(ri + 1) * CELL_H, ci * CELL_W:(ci + 1) * CELL_W] = tried[ci, best_k][1]
for (ri, ci), (top, bottom, x0, x1) in cells.items():
    # 角色超出格子会被裁掉，提醒一下
    if (bottom - top + 1) / block > CELL_H or (x1 - x0 + 1) / block > CELL_W + 4:
        print(f"注意：第 {ri + 1} 行第 {ci + 1} 列的角色超出了 {CELL_W}x{CELL_H} 的格子，可以加大 --cell")

# 补洞：被不透明像素围住（4 邻居里至少 3 个不透明）的透明点，用邻居颜色填上
for _ in range(2):
    a = sheet[..., 3] > 0
    fill = []
    for y in range(1, sheet.shape[0] - 1):
        for x in range(1, sheet.shape[1] - 1):
            if a[y, x]:
                continue
            solid = [p for p in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)) if a[p]]
            if len(solid) >= 3:
                fill.append((y, x, sheet[solid[0]].copy()))
    for y, x, c in fill:
        sheet[y, x] = c

if args.strip_tool:
    # 工具抠掉后会剩下它的黑色描边：没有挨着任何非黑色像素的黑点就是孤立描边，删掉
    for _ in range(3):
        a = sheet[..., 3] > 0
        lum = sheet[..., :3].astype(int).mean(2)
        dark = a & (lum < 70)
        body = a & ~dark
        near_body = np.zeros_like(body)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                near_body |= np.roll(np.roll(body, dy, 0), dx, 1)
        sheet[dark & ~near_body] = 0


def grow(mask, n):
    """八邻域膨胀 n 次（格子边界外当作空）。"""
    for _ in range(n):
        p = np.pad(mask, 1)
        mask = np.zeros_like(mask)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                mask |= p[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
    return mask


def outside(mask):
    """从格子边缘出发，四邻域能走到的空白；走不到的空白就是身体里的洞。"""
    out = np.zeros_like(mask)
    stack = [(y, x) for y in range(mask.shape[0]) for x in (0, mask.shape[1] - 1) if not mask[y, x]]
    stack += [(y, x) for x in range(mask.shape[1]) for y in (0, mask.shape[0] - 1) if not mask[y, x]]
    for y, x in stack:
        out[y, x] = True
    while stack:
        y, x = stack.pop()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and not mask[ny, nx] and not out[ny, nx]:
                out[ny, nx] = True
                stack.append((ny, nx))
    return out


for ri in range(args.rows):
    for ci in range(args.cols):
        cell = sheet[ri * CELL_H:(ri + 1) * CELL_H, ci * CELL_W:(ci + 1) * CELL_W]  # 视图，改它就是改 sheet
        a = cell[..., 3] > 0

        # 每格只保留最大的那块（身体）：飘着的工具碎片、闪光点之类都删掉
        label = np.zeros(a.shape, dtype=int)
        sizes = [0]
        for sy, sx in zip(*np.where(a)):
            if label[sy, sx]:
                continue
            sizes.append(0)
            stack = [(sy, sx)]
            label[sy, sx] = len(sizes) - 1
            while stack:
                y, x = stack.pop()
                sizes[-1] += 1
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < a.shape[0] and 0 <= nx < a.shape[1] and a[ny, nx] and not label[ny, nx]:
                            label[ny, nx] = len(sizes) - 1
                            stack.append((ny, nx))
        if len(sizes) > 2:
            keep = int(np.argmax(sizes))
            cell[(label != keep) & a] = 0
            a = cell[..., 3] > 0

        # 补洞：工具挡在身前，抠掉后身体中间会空一块。四面被身体围住的空白是洞；
        # 再把轮廓"闭合"一格（膨胀 1 再收缩 1），补上 1~2 像素宽的小缺口（双脚之间的缝更宽，不会被填）。
        # 然后用周围颜色一圈圈往里填
        closed = ~grow(outside(grow(a, 1)), 1)
        hole = ~a & (~outside(a) | closed)
        while hole.any():
            filled_any = False
            for y, x in zip(*np.where(hole)):
                nb = [cell[ny, nx] for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1))
                      if 0 <= ny < a.shape[0] and 0 <= nx < a.shape[1] and cell[ny, nx, 3] > 0]
                if nb:
                    # 优先用非描边色，免得洞被填成一片黑
                    light = [c for c in nb if c[:3].astype(int).mean() >= 70]
                    cell[y, x] = (light or nb)[0]
                    hole[y, x] = False
                    filled_any = True
            if not filled_any:
                break

Image.fromarray(sheet, "RGBA").save(args.out)
if args.preview:
    big = Image.fromarray(sheet, "RGBA").resize((sheet.shape[1] * 8, sheet.shape[0] * 8), Image.NEAREST)
    canvas = Image.new("RGBA", big.size, (200, 210, 190, 255))
    canvas.alpha_composite(big)
    canvas.save(args.preview)
print("saved", args.out)
