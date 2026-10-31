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
ap.add_argument("--palette", default="", help="共用调色板（make_palette.py 生成）；不给就每张图自己挑颜色")
ap.add_argument("--ref", default="", help="用第 r,c 格（从 0 数）的高度定比例：这一格缩成 --height 高")
ap.add_argument("--strip-tool", action="store_true", help="抠掉灰色工具头、棕色手柄/鱼竿、灰蓝水壶（游戏会自己画工具）")
ap.add_argument("--front", default="", help="正脸格子，取样时优先保证左右对称：'0' 是第 0 行整行，'1:3' 是第 1 行第 3 列，逗号分隔")
ap.add_argument("--dark-priority", type=float, default=0.0, help="一块里深色占到这个比例就取深色（保住闭眼这种细线），比如 0.25；0 表示关闭。只在脸上、且只对 --dark-cells 里的格子生效")
ap.add_argument("--dark-cells", default="", help="开深色优先的格子（格式同 --front）；会把嘴巴也加粗，所以只给闭眼的帧用")
ap.add_argument("--eye-gap", type=int, default=0, help="正脸两只瞳孔内侧之间统一隔几格（比如 4）；0 表示不调整")
ap.add_argument("--keep-eyes", default="", help="正脸里本来就不对称的格子（比如歪头），不做眼睛镜像；格式同 --front")
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

if args.palette:
    # 所有贴图共用一套颜色（make_palette.py 生成），肤色、发色、描边在每张图里都一样
    palette = np.array(Image.open(args.palette).convert("RGB")).reshape(-1, 3).astype(int)
    _pal_img = Image.new("P", (1, 1))
    # 调色板要填满 256 色；空位用第一种颜色重复，免得像素被映射到不存在的"黑色"序号上
    _pal_img.putpalette(palette.astype(np.uint8).flatten().tolist() + palette[0].tolist() * (256 - len(palette)))
    qidx = np.array(Image.fromarray(im.astype(np.uint8)).quantize(palette=_pal_img, dither=Image.Dither.NONE))
else:
    _q = Image.fromarray(np.where(fg[..., None], im, 0).astype(np.uint8)).quantize(
        colors=args.colors + 1, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    qidx = np.array(_q)
    palette = np.array(_q.getpalette()[:3 * (args.colors + 1)]).reshape(-1, 3)
DARK = palette.mean(1) < 60  # 描边、眼线、嘴这类深色
SKIN = (palette[:, 0] >= 235) & (palette[:, 2] <= 245) & (palette[:, 0] - palette[:, 2] >= 10)


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

def in_cells(spec, ri, ci):
    """格子列表："0" 表示第 0 行整行，"1:3" 表示第 1 行第 3 列，逗号分隔。"""
    for item in filter(None, spec.split(",")):
        r_, _, c_ = item.partition(":")
        if int(r_) == ri and (not c_ or int(c_) == ci):
            return True
    return False


def is_front(ri, ci):
    return in_cells(args.front, ri, ci)


def sample(cfg, bottom, head_cx, dx, dy, dark_on=False):
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
            counts = np.bincount(qidx[ya:yb, xa:xb][fgb], minlength=len(palette))
            purity.append(counts.max() / counts.sum())
            pick = counts.argmax()
            # 闭着的眼睛、嘴巴这种细线只有半个块高，按"谁最多"会被肤色吃掉；
            # 深色占到 --dark-priority 以上就取深色，保住细线
            # 只在脸上（块里有不少肤色）这么做，身上的描边保持原来的粗细
            dark = counts * DARK
            if (dark_on and args.dark_priority and not DARK[pick] and dark.sum() >= args.dark_priority * counts.sum()
                    and (counts * SKIN).sum() >= 0.3 * counts.sum()):
                pick = dark.argmax()
            out[ty, tx] = [*palette[pick].astype(np.uint8), 255]
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


def source_eye_mid(cfg, top, bottom):
    """
    在高清原图里找两只眼睛的瞳孔（偏亮的蓝），返回两只瞳孔中心的正中间（原图 x 坐标）。
    只在刘海下面露出的脸（肤色范围）里找，免得把头发高光当成瞳孔；闭着眼睛找不到就返回 None。
    """
    h = bottom - top
    rr, gg, bb = r, g, b
    skin_src = cfg & (rr >= 235) & (rr - bb >= 20)
    skin_src[:top + int(h * 0.15)] = False
    skin_src[top + int(h * 0.6):] = False
    ys, xs = np.where(skin_src)
    if len(ys) < 50:
        return None
    y_lo, y_hi = ys.min(), ys.min() + int(h * 0.25)
    lum = (rr + gg + bb) / 3
    iris = cfg & (bb > 200) & (bb - rr > 90) & (lum > 120)
    iris[:y_lo] = False
    iris[y_hi:] = False
    iris[:, :xs.min()] = False
    iris[:, xs.max() + 1:] = False
    iy, ix = np.where(iris)
    if len(ix) < 20:
        return None
    # 按 x 方向最大的空隙分成左右两团
    ux = np.unique(ix)
    if len(ux) < 2:
        return None
    cut = ux[np.argmax(np.diff(ux))]
    left, right = ix[ix <= cut], ix[ix > cut]
    if len(left) < 8 or len(right) < 8:
        return None
    # 两只瞳孔内侧之间的空隙（取 95%/5% 分位，避开零星噪点）
    gap = np.percentile(right, 5) - np.percentile(left, 95)
    return (left.mean() + right.mean()) / 2, gap


def eye_gap(cell, axis):
    """像素图里两只瞳孔（偏亮的蓝）内侧之间隔了几格；找不到返回 None。"""
    rows = np.where((cell[..., 3] > 0).any(1))[0]
    if len(rows) == 0:
        return None
    part = cell[rows[0] + 7:rows[0] + 18].astype(int)
    op = part[..., 3] > 0
    iris = op & (part[..., 2] > 195) & (part[..., 2] - part[..., 0] > 100)
    skin_ = op & (part[..., 0] >= 235) & (part[..., 2] <= 245) & (part[..., 0] - part[..., 2] >= 10)
    # 只认紧挨着皮肤的亮蓝：头发上的高光不贴脸，不会被误当成瞳孔
    touch = np.zeros_like(skin_)
    touch[:, 1:] |= skin_[:, :-1]
    touch[:, :-1] |= skin_[:, 1:]
    iris &= touch
    best = None
    for y in range(part.shape[0]):
        xs = np.where(iris[y])[0]
        left, right = xs[xs < axis], xs[xs > axis]
        if len(left) and len(right):
            gap = right.min() - left.max() - 1
            best = gap if best is None else min(best, gap)
    return best


EYE_AXIS = {}  # (ri, ci) -> 像素图里的眼睛中线
for ri in range(args.rows):
    tried = {}  # (ci, 偏移序号) -> (分数, 图)
    geom = {}  # ci -> (head_cx, 原图里的两眼中点)
    for ci in range(args.cols):
        top, bottom, x0, x1 = cells[ri, ci]
        own = np.zeros_like(fg)
        own[top:bottom + 1, x0:x1 + 1] = True
        cfg = fg & own
        head_bottom = top + int((bottom - top) * 0.4)
        hx = np.where(cfg[top:head_bottom + 1].any(0))[0]
        head_cx = (hx.min() + hx.max()) / 2
        front = is_front(ri, ci)
        geom[ci] = (head_cx, source_eye_mid(cfg, top, bottom) if front else None)
        for k, (fx, fy) in enumerate(OFFSETS):
            cand, purity = sample(cfg, bottom, head_cx, fx * block, fy * block, in_cells(args.dark_cells, ri, ci))
            tried[ci, k] = (purity + (2.0 * symmetry(cand) if front else 0.0), cand)
    best_k = max(range(len(OFFSETS)), key=lambda k: sum(tried[ci, k][0] for ci in range(args.cols)))
    for ci in range(args.cols):
        k_use = best_k
        head_cx, eyes = geom[ci]

        def out_axis(k):
            # 原图 x -> 像素图列号：第 tx 列取的是从 head_cx + (tx - W/2)*block + dx 开始的那一块
            tx = (eyes[0] - head_cx - OFFSETS[k][0] * block) / block + CELL_W / 2 - 0.5
            return round(tx * 2) / 2

        if eyes is not None:
            EYE_AXIS[ri, ci] = out_axis(k_use)
        sheet[ri * CELL_H:(ri + 1) * CELL_H, ci * CELL_W:(ci + 1) * CELL_W] = tried[ci, k_use][1]
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

def mirror_eyes(cell, known_axis=None):
    """
    正脸的眼睛只有 2~3 像素宽，取样稍微错开一点就一大一小。
    找到刘海下面露出的脸（肤色）最上面那行，取它上 1 行到下 3 行（眼睛那一带），按头的中线左右镜像：
    哪一半脸上的"非肤色"像素多（眼睛画得更完整），就用那一半盖住另一半。
    """
    rgb = cell[..., :3].astype(int)
    opaque = cell[..., 3] > 0
    skin = opaque & (rgb[..., 0] >= 235) & (rgb[..., 2] <= 245) & (rgb[..., 0] - rgb[..., 2] >= 10)
    rows = np.where(opaque.any(1))[0]
    if len(rows) == 0:
        return
    # 只看头部：上面 7 行是白色女仆头饰（颜色和皮肤几乎一样，会被误当成脸），下面别把手和腿算进来
    skin[:rows[0] + 7] = False
    skin[rows[0] + 20:] = False
    ys, xs = np.where(skin)
    if len(ys) < 8:
        return  # 背面或侧脸，没有正脸
    # 刘海下沿第一行露出的皮肤就在眼睛那一带：从它上面 1 行到下面 3 行
    y0, y1 = max(ys.min() - 1, 0), min(ys.min() + 3, cell.shape[0] - 1)
    fx0, fx1 = xs.min() - 1, xs.max() + 1  # 脸的左右范围（多留一格描边）
    band = slice(y0, y1 + 1)
    # 中线：不能按头发左右边缘算（她一边头发更蓬，中线会偏、镜像后两眼间距变大）。
    # 在脸中心附近试几条候选线，挑现有眼睛本来就最对称的那条，这样只修大小、不改间距
    c0 = (xs.min() + xs.max()) / 2
    eyes = (cell[band, :, 3] > 0) & ~skin[band]

    def axis_score(ax):
        same = total = 0
        for x in range(max(fx0, 0), min(fx1, cell.shape[1] - 1) + 1):
            mx = int(round(2 * ax - x))
            if mx <= x or not (fx0 <= mx <= fx1) or mx >= cell.shape[1]:
                continue
            for y in range(eyes.shape[0]):
                if eyes[y, x] or eyes[y, mx]:
                    total += 1
                    same += bool((cell[y0 + y, x] == cell[y0 + y, mx]).all())
        return same / total if total else 0.0

    # 原图里找到了瞳孔就直接用两只瞳孔的正中间（最准）；闭眼等找不到时才用上面的对称度来猜
    axis = known_axis if known_axis is not None else max(np.arange(round(c0 * 2) / 2 - 2, round(c0 * 2) / 2 + 2.01, 0.5), key=axis_score)

    def eye_pixels(lo, hi):
        part = cell[band, max(lo, 0):hi]
        sk = skin[band, max(lo, 0):hi]
        return int(((part[..., 3] > 0) & ~sk).sum())

    left = eye_pixels(fx0, int(np.ceil(axis)))
    right = eye_pixels(int(np.floor(axis)) + 1, fx1 + 1)
    # 只镜像脸的范围，两侧的头发和鳍耳保持原样，免得这几行和上下接不上
    src_cols = range(max(fx0, 0), int(np.ceil(axis))) if left >= right else range(int(np.floor(axis)) + 1, fx1 + 1)
    for x in src_cols:
        mx = int(round(2 * axis - x))
        if fx0 <= mx <= fx1 and 0 <= mx < cell.shape[1] and mx != x:
            cell[band, mx] = cell[band, x]

    # 统一眼距：原图里每帧两只瞳孔内侧都隔约 3.5 格，缩小后有的帧被刘海挤成 2 格、两眼显得太近。
    # 量出现在的间隙，把左眼整体往外/往里挪，再镜像到右边
    if known_axis is None or not args.eye_gap:
        return
    gap = eye_gap(cell, axis)
    want = args.eye_gap if axis % 1 else args.eye_gap - 1  # 中线在两列之间时间隙是偶数，在某列正中时是奇数
    if gap is None or gap == want or (want - gap) % 2:
        return
    d = (want - gap) // 2  # 每只眼往外挪几格（负数是往里）
    inner = int(np.ceil(axis)) - 1  # 中线左边紧挨着的那一列
    lo = max(fx0, 0)
    orig = cell[band].copy()
    if d > 0:
        for x in range(lo - d, inner - d + 1):
            if x >= 0:
                cell[band, x] = orig[:, x + d]
        for x in range(inner - d + 1, inner + 1):
            cell[band, x] = orig[:, inner]  # 空出来的是两眼之间，用原来中间那一列（皮肤/刘海）补
    else:
        k = -d
        for x in range(inner, lo + k - 1, -1):
            cell[band, x] = orig[:, x - k]
        for x in range(lo, lo + k):
            cell[band, x] = orig[:, lo]
    for x in range(max(lo - max(d, 0), 0), inner + 1):
        mx = int(round(2 * axis - x))
        if 0 <= mx < cell.shape[1] and mx != x:
            cell[band, mx] = cell[band, x]


for ri in range(args.rows):
    for ci in range(args.cols):
        if is_front(ri, ci) and not in_cells(args.keep_eyes, ri, ci):
            mirror_eyes(sheet[ri * CELL_H:(ri + 1) * CELL_H, ci * CELL_W:(ci + 1) * CELL_W], EYE_AXIS.get((ri, ci)))

Image.fromarray(sheet, "RGBA").save(args.out)
if args.preview:
    big = Image.fromarray(sheet, "RGBA").resize((sheet.shape[1] * 8, sheet.shape[0] * 8), Image.NEAREST)
    canvas = Image.new("RGBA", big.size, (200, 210, 190, 255))
    canvas.alpha_composite(big)
    canvas.save(args.preview)
print("saved", args.out)
