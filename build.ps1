# 编译模组并直接装进星露谷的 Mods 文件夹
param(
    [string]$GamePath = "E:\SteamLibrary\steamapps\common\Stardew Valley"
)
$env:DOTNET_ROOT = "E:\Darian\Downloads\toolchain\dotnet"
$env:NUGET_PACKAGES = "E:\Darian\Downloads\toolchain\nuget"
$env:DOTNET_CLI_HOME = "E:\Darian\Downloads\toolchain\clihome"
& "E:\Darian\Downloads\toolchain\dotnet\dotnet.exe" build "$PSScriptRoot\WhaleFarmer" -c Release
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$ErrorActionPreference = "Stop"  # 游戏开着时 dll 会被占用，复制失败要报错而不是假装装好了
$out = "$PSScriptRoot\WhaleFarmer\bin\Release\net6.0"
$dst = Join-Path $GamePath "Mods\WhaleFarmer"
New-Item -ItemType Directory -Force "$dst\assets" | Out-Null
Copy-Item "$out\WhaleFarmer.dll", "$out\manifest.json" $dst -Force
Copy-Item "$out\assets\*" "$dst\assets\" -Force
Write-Host "已编译并安装到 $dst" -ForegroundColor Green
