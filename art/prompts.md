# 蓝色大肥鱼：姿态图提示词

每次都把 `1-full.png`（已经做好的走路图）作为参考图一起发给 GPT，尺寸选竖版 1024x1536。
生成好后按编号存到这个文件夹：4-tools.png、5-melee.png、6-crouch.png、7-fishing.png、8-eat.png、9-misc.png。

下面每段开头的“通用要求”都一样，已经写在每段里了，直接整段复制就行。

---

## 4-tools.png：挥锄头 / 斧头 / 镐子

```text
Use the attached sprite sheet as the exact character and style reference (same girl, same pixel size, same palette, same outline, same proportions).

Draw a new pixel art sprite sheet of her swinging a heavy farming tool (a hoe) with both hands, Stardew Valley style.
Layout: 3 rows x 4 columns, evenly spaced, one pose per cell, each pose drawn at the SAME scale as the reference (about 22 pixels wide and 30 pixels tall in true pixel resolution, upscaled with nearest-neighbor, crisp square pixels, no anti-aliasing).
Row 1: facing down (toward camera). Row 2: facing right. Row 3: facing up (back view).
Columns: 1 = tool raised high above head, 2 = swinging down halfway, 3 = tool head hitting the ground in front of her, 4 = recovering, tool resting on the ground.
Feet stay on the same ground line in every cell. Tool handle brown, tool head grey.
Solid flat magenta background (#FF00FF), no shadows, no ground, no text, no grid lines, clear empty gaps between poses.
```

## 5-melee.png：挥剑 / 镰刀

```text
Use the attached sprite sheet as the exact character and style reference (same girl, same pixel size, same palette, same outline, same proportions).

Draw a new pixel art sprite sheet of her swinging a short sword in a sideways slash, Stardew Valley style.
Layout: 3 rows x 4 columns, evenly spaced, one pose per cell, each pose drawn at the SAME scale as the reference (about 22 pixels wide and 30 pixels tall in true pixel resolution, upscaled with nearest-neighbor, crisp square pixels, no anti-aliasing).
Row 1: facing down (toward camera). Row 2: facing right. Row 3: facing up (back view).
Columns: 1 = wind-up, arm pulled back, 2 = mid-slash, 3 = arm fully extended at the end of the slash, 4 = follow-through, arm across the body.
Do NOT draw the sword itself (the game draws it), only her arm and hand positions.
Feet stay on the same ground line in every cell.
Solid flat magenta background (#FF00FF), no shadows, no ground, no text, no grid lines, clear empty gaps between poses.
```

## 6-crouch.png：收菜 / 捡东西 / 浇水 / 挤奶

```text
Use the attached sprite sheet as the exact character and style reference (same girl, same pixel size, same palette, same outline, same proportions).

Draw a new pixel art sprite sheet of her working close to the ground, Stardew Valley style.
Layout: 3 rows x 4 columns, evenly spaced, one pose per cell, each pose drawn at the SAME scale as the reference (about 22 pixels wide, up to 30 pixels tall in true pixel resolution, upscaled with nearest-neighbor, crisp square pixels, no anti-aliasing).
Row 1: facing down (toward camera). Row 2: facing right. Row 3: facing up (back view).
Columns: 1 = crouching and reaching one hand toward the ground, 2 = crouching and grabbing something from the ground, 3 = standing and holding a watering can forward with both hands, 4 = standing and tilting the watering can down to pour.
Feet stay on the same ground line in every cell. Watering can is light grey-blue.
Solid flat magenta background (#FF00FF), no shadows, no ground, no text, no grid lines, clear empty gaps between poses.
```

## 7-fishing.png：钓鱼

```text
Use the attached sprite sheet as the exact character and style reference (same girl, same pixel size, same palette, same outline, same proportions).

Draw a new pixel art sprite sheet of her fishing, Stardew Valley style.
Layout: 3 rows x 3 columns, evenly spaced, one pose per cell, each pose drawn at the SAME scale as the reference (about 22 pixels wide and 30 pixels tall in true pixel resolution, upscaled with nearest-neighbor, crisp square pixels, no anti-aliasing).
Row 1: facing down (toward camera). Row 2: facing right. Row 3: facing up (back view).
Columns: 1 = calmly holding a fishing rod forward and waiting, 2 = reeling in, leaning back and pulling the rod up, 3 = reeling in, leaning forward with the rod lower.
Do NOT draw the fishing line. Rod is thin and brown.
Feet stay on the same ground line in every cell.
Solid flat magenta background (#FF00FF), no shadows, no ground, no text, no grid lines, clear empty gaps between poses.
```

## 8-eat.png：吃喝 / 举起东西

```text
Use the attached sprite sheet as the exact character and style reference (same girl, same pixel size, same palette, same outline, same proportions).

Draw a new pixel art sprite sheet of her eating and drinking, always facing down toward the camera, Stardew Valley style.
Layout: 1 row x 6 columns, evenly spaced, one pose per cell, each pose drawn at the SAME scale as the reference (about 22 pixels wide and 30 pixels tall in true pixel resolution, upscaled with nearest-neighbor, crisp square pixels, no anti-aliasing).
Columns: 1 = proudly holding both empty hands up above her head (showing off an item, the game draws the item), 2 = bringing empty hands to her mouth, 3 = chewing with eyes closed and cheeks puffed, 4 = chewing happily with a smile, 5 = tilting her head back holding an empty hand to her mouth like drinking, 6 = drinking with eyes closed.
Do NOT draw any food or item in her hands.
Feet stay on the same ground line in every cell.
Solid flat magenta background (#FF00FF), no shadows, no ground, no text, no grid lines, clear empty gaps between poses.
```

## 9-misc.png：坐下 / 晕倒 / 表情

```text
Use the attached sprite sheet as the exact character and style reference (same girl, same pixel size, same palette, same outline, same proportions).

Draw a new pixel art sprite sheet of her in various poses, Stardew Valley style.
Layout: 2 rows x 4 columns, evenly spaced, one pose per cell, each pose drawn at the SAME scale as the reference (about 22 pixels wide, up to 30 pixels tall in true pixel resolution, upscaled with nearest-neighbor, crisp square pixels, no anti-aliasing).
Row 1: 1 = sitting (as if riding a horse) facing down toward the camera, legs apart, 2 = sitting facing right, 3 = sitting facing up (back view), 4 = lying flat on the ground asleep, seen from the side, head on the left.
Row 2, all facing down toward the camera: 1 = shocked with wide eyes and hands up, 2 = laughing with eyes closed and a hand near the mouth, 3 = feeling sick, slouched with a pale face, 4 = shy and blushing with hands clasped.
Bottom of every pose on the same ground line.
Solid flat magenta background (#FF00FF), no shadows, no ground, no text, no grid lines, clear empty gaps between poses.
```
