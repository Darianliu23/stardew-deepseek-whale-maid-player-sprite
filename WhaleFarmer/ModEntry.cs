using System;
using System.Collections.Generic;
using System.IO;
using HarmonyLib;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;

namespace WhaleFarmer
{
    public class ModEntry : Mod
    {
        /// <summary>每张姿态表的文件名和网格（列 x 行）。走路表是 4 行：朝下、朝右、朝上、朝左；其他三行的表朝左用朝右镜像。</summary>
        private static readonly Dictionary<Sheet, (string File, int Cols, int Rows)> SheetLayout = new()
        {
            [Sheet.Walk] = ("walk.png", 4, 4),
            [Sheet.Tools] = ("tools.png", 4, 3),
            [Sheet.Melee] = ("melee.png", 4, 3),
            [Sheet.Crouch] = ("crouch.png", 4, 3),
            [Sheet.Fishing] = ("fishing.png", 3, 3),
            [Sheet.Eat] = ("eat.png", 6, 1),
            [Sheet.Misc] = ("misc.png", 4, 2)
        };

        private static ModEntry instance;
        private ModConfig config;
        private readonly Dictionary<Sheet, Texture2D> sheets = new();

        public override void Entry(IModHelper helper)
        {
            instance = this;
            config = helper.ReadConfig<ModConfig>();

            foreach (var (sheet, layout) in SheetLayout)
            {
                if (!File.Exists(Path.Combine(helper.DirectoryPath, "assets", layout.File)))
                    continue;
                try
                {
                    sheets[sheet] = helper.ModContent.Load<Texture2D>("assets/" + layout.File);
                }
                catch (Exception ex)
                {
                    Monitor.Log($"读取 assets/{layout.File} 失败：{ex.Message}", LogLevel.Warn);
                }
            }
            if (!sheets.ContainsKey(Sheet.Walk))
            {
                Monitor.Log("缺少 assets/walk.png，保持原版外观。", LogLevel.Error);
                return;
            }

            var harmony = new Harmony(ModManifest.UniqueID);
            // 只拦截最底层的那个 draw 重载：其他重载最终都会调用它
            harmony.Patch(
                AccessTools.Method(typeof(FarmerRenderer), nameof(FarmerRenderer.draw), new[]
                {
                    typeof(SpriteBatch), typeof(FarmerSprite.AnimationFrame), typeof(int), typeof(Rectangle),
                    typeof(Vector2), typeof(Vector2), typeof(float), typeof(int), typeof(Color),
                    typeof(float), typeof(float), typeof(Farmer)
                }),
                prefix: new HarmonyMethod(typeof(ModEntry), nameof(DrawPrefix)));
            // 菜单标签、地图、锻造台、多人状态栏用的小头像走的是另一个函数
            harmony.Patch(
                AccessTools.Method(typeof(FarmerRenderer), nameof(FarmerRenderer.drawMiniPortrat)),
                prefix: new HarmonyMethod(typeof(ModEntry), nameof(MiniPortraitPrefix)));

            // 这些模组也会接管农夫的绘制，同时开着可能画出两个人
            foreach (string id in new[] { "PeacefulEnd.FashionSense" })
                if (helper.ModRegistry.IsLoaded(id))
                    Monitor.Log($"检测到 {helper.ModRegistry.Get(id).Manifest.Name}，它和鲸鱼娘外观都会改农夫的绘制，可能冲突。", LogLevel.Warn);

            helper.Events.Input.ButtonPressed += OnButtonPressed;
            var missing = new List<string>();
            foreach (var (sheet, layout) in SheetLayout)
                if (!sheets.ContainsKey(sheet))
                    missing.Add(layout.File);
            Monitor.Log($"鲸鱼娘外观已加载，按 {config.ToggleKey} 切换。"
                + (missing.Count > 0 ? $" 还没有的姿态图（用站立姿势代替）：{string.Join("、", missing)}" : ""), LogLevel.Info);
        }

        private void OnButtonPressed(object sender, ButtonPressedEventArgs e)
        {
            if (e.Button != config.ToggleKey || !Context.IsPlayerFree)
                return;
            config.Enabled = !config.Enabled;
            Helper.WriteConfig(config);
            Game1.addHUDMessage(new HUDMessage(config.Enabled ? "鲸鱼娘外观：开" : "鲸鱼娘外观：关", HUDMessage.newQuest_type));
        }

        /// <summary>返回 false 表示跳过原版绘制（身体、裤子、衣服、头发、帽子、手臂都不画）。</summary>
        private static bool DrawPrefix(SpriteBatch b, FarmerSprite.AnimationFrame animationFrame, int currentFrame,
            Vector2 position, Vector2 origin, float layerDepth, int facingDirection, Color overrideColor,
            float rotation, float scale, Farmer who)
        {
            var self = instance;
            if (self == null || !self.ShouldReplace(who))
                return true;
            try
            {
                self.DrawWhale(b, animationFrame, currentFrame, position, origin, layerDepth, facingDirection, overrideColor, rotation, scale, who);
                return false;
            }
            catch (Exception ex)
            {
                // 画失败就退回原版，不能让游戏崩
                self.Monitor.LogOnce("绘制鲸鱼娘出错，退回原版外观：" + ex, LogLevel.Error);
                return true;
            }
        }

        /// <summary>只替换真正的玩家：人体模特等用临时 Farmer 画的东西保持原样。</summary>
        private bool ShouldReplace(Farmer who)
        {
            if (!config.Enabled || who == null || !sheets.ContainsKey(Sheet.Walk))
                return false;
            if (who.IsLocalPlayer)
                return true;
            return !config.OnlyLocalPlayer && Game1.getOnlineFarmers().Contains(who);
        }

        /// <summary>小头像：从朝下站立那一帧裁出头部（第 6~20 行、第 5~26 列），缩到和原版头像一样宽。</summary>
        private static bool MiniPortraitPrefix(SpriteBatch b, Vector2 position, float layerDepth, float scale, Farmer who, float alpha)
        {
            var self = instance;
            if (self == null || !self.ShouldReplace(who))
                return true;
            var head = new Rectangle(5, 6, 22, 15);
            float s = scale * 16f / head.Width;
            // 原版头像高 15 格，我们的头缩完会矮一点，往下挪让下巴对齐
            var pos = position + new Vector2(0f, (15f - head.Height * 16f / head.Width) * scale);
            b.Draw(self.sheets[Sheet.Walk], pos, head, Color.White * alpha, 0f, Vector2.Zero, s, SpriteEffects.None, layerDepth);
            return false;
        }

        private void DrawWhale(SpriteBatch b, FarmerSprite.AnimationFrame animationFrame, int currentFrame, Vector2 position,
            Vector2 origin, float layerDepth, int facingDirection, Color overrideColor, float rotation, float scale, Farmer who)
        {
            var frame = Poses.Resolve(currentFrame, animationFrame.flip, who);
            if (frame == null || !sheets.ContainsKey(frame.Value.Sheet))
                frame = WalkFrame(animationFrame, facingDirection, who);
            var pose = frame.Value;

            var texture = sheets[pose.Sheet];
            var layout = SheetLayout[pose.Sheet];
            int w = texture.Width / layout.Cols, h = texture.Height / layout.Rows;
            var src = new Rectangle(pose.Col * w, pose.Row * h, w, h);

            position = new Vector2((float)Math.Floor(position.X), (float)Math.Floor(position.Y));
            var offset = new Vector2(animationFrame.xOffset * 4, animationFrame.positionOffset * 4);

            // 游泳时只露出上半身，和原版一样往下挪 64 像素
            if (!FarmerRenderer.isDrawingForUI && who.swimming.Value)
            {
                src.Height -= 16;
                position.Y += 64f;
            }

            // 原版身体是 16x32；我们的格子水平居中、脚底对齐到同一位置
            var ourOrigin = origin + new Vector2((w - 16) / 2f, h - 32);
            b.Draw(texture, position + origin + offset, src, overrideColor, rotation, ourOrigin, 4f * scale,
                pose.Flip ? SpriteEffects.FlipHorizontally : SpriteEffects.None,
                FarmerRenderer.GetLayerDepth(layerDepth, FarmerRenderer.FarmerSpriteLayers.Base));
        }

        /// <summary>走路/站立：走路表有单独的朝左一行，不用镜像。</summary>
        private PoseFrame WalkFrame(FarmerSprite.AnimationFrame animationFrame, int facingDirection, Farmer who)
        {
            if (facingDirection == 1 || facingDirection == 3)
                facingDirection = animationFrame.flip ? 3 : 1;
            int row = facingDirection switch { 2 => 0, 1 => 1, 0 => 2, _ => 3 };

            int col = 0;
            if (!FarmerRenderer.isDrawingForUI && (who.isMoving() || MovedRecently(who)) && !who.UsingTool)
            {
                int ms = who.running ? config.WalkFrameMs * 2 / 3 : config.WalkFrameMs;
                col = (int)(Game1.currentGameTime.TotalGameTime.TotalMilliseconds / ms) % 4;
            }
            return new PoseFrame(Sheet.Walk, row, col);
        }

        /// <summary>每个玩家上一次看到的坐标、所在帧、判定为“在走”的截止帧。</summary>
        private readonly Dictionary<long, (Vector2 Pos, int Tick, int MovingUntil)> lastPositions = new();

        /// <summary>
        /// isMoving() 只看方向键输入；其他模组（比如 AI 代玩）直接改坐标走路时它是 false。
        /// 这里改看坐标有没有变，留 2 帧余量，防止某一帧没挪动时闪回站立。
        /// </summary>
        private bool MovedRecently(Farmer who)
        {
            int now = Game1.ticks;
            long id = who.UniqueMultiplayerID;
            if (!lastPositions.TryGetValue(id, out var rec))
            {
                lastPositions[id] = (who.Position, now, -1);
                return false;
            }
            if (rec.Tick != now)
            {
                var delta = who.Position - rec.Pos;
                // 一帧挪了好几格是传送/切地图，不算走路
                bool walked = delta != Vector2.Zero && delta.LengthSquared() < 64f * 64f;
                rec = (who.Position, now, walked ? now + 2 : rec.MovingUntil);
                lastPositions[id] = rec;
            }
            return now <= rec.MovingUntil;
        }
    }
}
