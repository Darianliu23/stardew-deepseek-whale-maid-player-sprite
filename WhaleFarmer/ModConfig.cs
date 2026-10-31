using StardewModdingAPI;

namespace WhaleFarmer
{
    public class ModConfig
    {
        /// <summary>是否启用鲸鱼娘外观。</summary>
        public bool Enabled { get; set; } = true;

        /// <summary>切换外观的快捷键。</summary>
        public SButton ToggleKey { get; set; } = SButton.F9;

        /// <summary>走路时每帧持续的毫秒数；跑步时自动加快。</summary>
        public int WalkFrameMs { get; set; } = 180;

        /// <summary>只替换自己（多人联机时其他玩家保持原样）。</summary>
        public bool OnlyLocalPlayer { get; set; } = true;
    }
}
