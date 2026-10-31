"""从所有原图里挑一套共用的调色板，让每张贴图的肤色、发色、描边颜色都一样。

用法:
  python make_palette.py 输出.png 原图1.png 原图2.png ... [--colors 22]

每张图各自压缩颜色时，肤色常常和女仆装的白色合并（脸变白或变灰），而且每张图挑出来的颜色都不一样。
这里先把所有原图的前景像素合在一起挑颜色（皮肤和腮红先拿出来），再单独加上原图的肤色，保证皮肤不会被并进白色。
输出是一张 1 像素高的小图，每个像素是一种颜色，给 pixelize.py 的 --palette 用。
"""
import argparse
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("sources", nargs="+")
ap.add_argument("--colors", type=int, default=22, help="除肤色以外挑几种颜色")
args = ap.parse_args()

pixels, skin_main, skin_shade = [], [], []
rng = np.random.default_rng(0)
for path in args.sources:
    a = np.array(Image.open(path).convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    fg = ~(((np.minimum(r, b) - g) > 110) & (g < 120))
    # 皮肤：很亮、偏暖；腮红/阴影：稍暗、更红
    main = fg & (r >= 235) & (r - b >= 25) & (r - b <= 70) & (g >= 195) & (g <= 240)
    shade = fg & (r >= 215) & (r - b >= 45) & (g >= 150) & (g < 205)
    skin_main.append(a[main])
    skin_shade.append(a[shade])
    rest = a[fg & ~main & ~shade]
    pixels.append(rest[rng.choice(len(rest), min(len(rest), 60000), replace=False)])

sample = np.concatenate(pixels).astype(np.uint8)
q = Image.fromarray(sample[None, :, :]).quantize(colors=args.colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
base = np.array(q.getpalette()[:3 * args.colors]).reshape(-1, 3)
# 只加一种肤色：腮红在 26 像素高的脸上只剩一两个像素，看着像斑点，不如直接并进肤色
skin = np.median(np.concatenate(skin_main + skin_shade), axis=0)
palette = np.vstack([base, np.round(skin)[None]]).astype(np.uint8)
Image.fromarray(palette[None, :, :]).save(args.out)
print("肤色:", palette[-1].tolist(), "共", len(palette), "色")
