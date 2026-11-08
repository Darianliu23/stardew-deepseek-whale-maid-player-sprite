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

        /// <summary>联机时其他玩家也开着鲸鱼娘外观，就在你的画面上把他们也画成鲸鱼娘（对方也要装这个模组）。</summary>
        public bool ShowOtherPlayers { get; set; } = true;

        /// <summary>切换“其他玩家显示成鲸鱼娘”的快捷键。</summary>
        public SButton ShowOthersKey { get; set; } = SButton.F10;
    }
}
