using System;
using StardewValley;
using StardewValley.Tools;

namespace WhaleFarmer
{
    /// <summary>姿态图：一张精灵表 + 网格尺寸。三行的表按"朝下、朝右、朝上"排列，朝左用朝右镜像。</summary>
    internal enum Sheet
    {
        Walk,
        Tools,
        Melee,
        Crouch,
        Fishing,
        Eat,
        Misc
    }

    /// <summary>要画的那一帧：哪张表、第几行第几列、是否水平翻转。</summary>
    internal readonly struct PoseFrame
    {
        public readonly Sheet Sheet;
        public readonly int Row;
        public readonly int Col;
        public readonly bool Flip;

        public PoseFrame(Sheet sheet, int row, int col, bool flip = false)
        {
            Sheet = sheet;
            Row = row;
            Col = col;
            Flip = flip;
        }
    }

    /// <summary>
    /// 把原版农夫的帧编号（见 Wiki: Modding:Farmer sprite）翻译成我们的姿态帧。
    /// 同一个帧编号在不同动作里会复用（比如 36~38 既是挥武器朝上，也是挥锄头朝上），所以先看手上的工具。
    /// </summary>
    internal static class Poses
    {
        // 三行姿态表的行号
        private const int Down = 0, Side = 1, Up = 2;

        /// <summary>返回 null 表示没有专门的姿态，按走路/站立处理。</summary>
        public static PoseFrame? Resolve(int frame, bool flip, Farmer who)
        {
            if (who.UsingTool && who.CurrentTool != null)
            {
                var byTool = ResolveTool(frame, flip, who, who.CurrentTool);
                if (byTool != null)
                    return byTool;
            }
            return ResolveGeneral(frame, flip, who);
        }

        private static PoseFrame? ResolveTool(int frame, bool flip, Farmer who, Tool tool)
        {
            switch (tool)
            {
                case FishingRod rod:
                    // 等鱼上钩：鱼竿往前伸着
                    if (frame == 70 || frame == 89 || frame == 44)
                        return Dir(Sheet.Fishing, frame == 70 ? Down : frame == 89 ? Side : Up, 0, flip);
                    // 小游戏收线：在两帧之间来回摆
                    if (rod.isReeling && (frame == 66 || frame == 48 || frame == 36))
                        return Dir(Sheet.Fishing, frame == 66 ? Down : frame == 48 ? Side : Up, 1 + Blink(250), flip);
                    // 抛竿复用挥重工具的动作
                    return HeavyTool(frame, flip);

                case MeleeWeapon:
                    if (frame >= 24 && frame <= 41)
                    {
                        int row = frame <= 29 ? Down : frame <= 35 ? Side : Up;
                        int step = (frame - 24) % 6; // 0..5
                        int[] cols = { 0, 1, 1, 2, 2, 3 };
                        return Dir(Sheet.Melee, row, cols[step], flip);
                    }
                    // 棒槌的特殊攻击用挥重工具的动作
                    return HeavyTool(frame, flip);

                case Slingshot:
                    if (frame >= 42 && frame <= 44)
                        return Dir(Sheet.Melee, frame - 42, 0, flip);
                    return null;

                case WateringCan:
                    // 先把水壶往前举，再倒水
                    if (frame == 54 || frame == 55) return Dir(Sheet.Crouch, Down, 2, flip);
                    if (frame == 58 || frame == 59) return Dir(Sheet.Crouch, Side, 2, flip);
                    if (frame == 62 || frame == 63) return Dir(Sheet.Crouch, Up, 2, flip);
                    if (frame == 25) return Dir(Sheet.Crouch, Down, 3, flip);
                    if (frame == 45) return Dir(Sheet.Crouch, Side, 3, flip);
                    if (frame == 46) return Dir(Sheet.Crouch, Up, 3, flip);
                    return HeavyTool(frame, flip);

                case MilkPail:
                case Shears:
                    if (frame >= 78 && frame <= 83)
                        return Dir(Sheet.Crouch, (frame - 78) / 2, 1 - frame % 2, flip);
                    return Harvest(frame, flip);

                case Pan:
                    if (frame >= 123 && frame <= 125)
                        return Dir(Sheet.Crouch, Down, frame == 123 ? 0 : 1, flip);
                    return null;

                default:
                    // 锄头、斧头、镐子等
                    return HeavyTool(frame, flip);
            }
        }

        private static PoseFrame? ResolveGeneral(int frame, bool flip, Farmer who)
        {
            var harvest = Harvest(frame, flip);
            if (harvest != null)
                return harvest;

            switch (frame)
            {
                // 举起物品（钓到鱼、拿到新东西）、吃东西
                case 84: return new PoseFrame(Sheet.Eat, 0, 0);
                case 85:
                case 86: return new PoseFrame(Sheet.Eat, 0, 1);
                case 87: return new PoseFrame(Sheet.Eat, 0, 2);
                case 88: return new PoseFrame(Sheet.Eat, 0, 3);
                // 喝东西
                case 90:
                case 91: return new PoseFrame(Sheet.Eat, 0, 4);
                case 92:
                case 93: return new PoseFrame(Sheet.Eat, 0, 5);

                // 骑马、坐下：杂项表第 1 行 = 朝下、朝右、朝上坐着
                case 107: return new PoseFrame(Sheet.Misc, 0, 0);
                case 106:
                case 117: return new PoseFrame(Sheet.Misc, 0, 1, flip);
                case 113: return new PoseFrame(Sheet.Misc, 0, 2);
                // 晕倒最后躺在地上
                case 5: return new PoseFrame(Sheet.Misc, 0, 3);

                // 杂项表第 2 行（都朝下）：吃惊、大笑、恶心、害羞亲亲
                case 16:
                case 94: return new PoseFrame(Sheet.Misc, 1, 0);
                case 97:
                case 102:
                case 103: return new PoseFrame(Sheet.Misc, 1, 1);
                case 4:
                case 95:
                case 96:
                case 104:
                case 105: return new PoseFrame(Sheet.Misc, 1, 2);
                case 101: return new PoseFrame(Sheet.Misc, 1, 3);

                // 钓到鱼后先举一下竿
                case 72:
                case 74:
                case 76: return HeavyTool(frame, flip);
            }
            return null;
        }

        /// <summary>挥锄头/斧头/镐子（以及抛竿、蓄力锄地）：举起、下落、砸地、收回 4 列。</summary>
        private static PoseFrame? HeavyTool(int frame, bool flip)
        {
            switch (frame)
            {
                case 66: case 74: case 75: return Dir(Sheet.Tools, Down, 0, flip);
                case 67: case 68: return Dir(Sheet.Tools, Down, 1, flip);
                case 69: return Dir(Sheet.Tools, Down, 2, flip);
                case 70: return Dir(Sheet.Tools, Down, 3, flip);

                case 48: case 72: case 73: return Dir(Sheet.Tools, Side, 0, flip);
                case 49: case 50: return Dir(Sheet.Tools, Side, 1, flip);
                case 51: return Dir(Sheet.Tools, Side, 2, flip);
                case 52: return Dir(Sheet.Tools, Side, 3, flip);

                case 36: case 76: case 77: return Dir(Sheet.Tools, Up, 0, flip);
                case 37: case 38: return Dir(Sheet.Tools, Up, 1, flip);
                case 63: return Dir(Sheet.Tools, Up, 2, flip);
                case 62: return Dir(Sheet.Tools, Up, 3, flip);
            }
            return null;
        }

        /// <summary>收菜、捡东西、挤奶：蹲下伸手（第 0 列）、抓住（第 1 列）。</summary>
        private static PoseFrame? Harvest(int frame, bool flip)
        {
            if (frame >= 54 && frame <= 65)
            {
                int row = frame <= 57 ? Down : frame <= 61 ? Side : Up;
                int step = (frame - 54) % 4; // 0..3
                return Dir(Sheet.Crouch, row, step == 0 || step == 3 ? 0 : 1, flip);
            }
            return null;
        }

        private static PoseFrame Dir(Sheet sheet, int row, int col, bool flip) =>
            new(sheet, row, col, row == Side && flip);

        /// <summary>按时间在 0 和 1 之间切换。</summary>
        private static int Blink(int ms) =>
            (int)(Game1.currentGameTime.TotalGameTime.TotalMilliseconds / ms) % 2;
    }
}
