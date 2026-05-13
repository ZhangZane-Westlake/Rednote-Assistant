#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  macOS DMG 打包脚本
#  在 Mac 上运行此脚本，一键生成 DMG
#
#  用法：
#    chmod +x build.sh
#    ./build.sh
#
#  输出：
#    xhs-assistant/dist/小红书笔记助手-1.0.0.dmg
# ═══════════════════════════════════════════════════════════

set -e

# ── 路径 ─────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist"
APP_NAME="小红书笔记助手"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
DMG_NAME="小红书笔记助手-v260514.dmg"
DMG_PATH="$DIST_DIR/$DMG_NAME"

echo "📕 开始打包 $APP_NAME …"
echo ""

# ── 清理旧的 ─────────────────────────────────
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# ── 创建 .app 目录结构 ────────────────────────
echo "📁 创建 .app 包结构…"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Info.plist
cp "$SCRIPT_DIR/Info.plist" "$APP_BUNDLE/Contents/"

# Launcher (executable)
cp "$SCRIPT_DIR/launcher.sh" "$APP_BUNDLE/Contents/MacOS/"
chmod +x "$APP_BUNDLE/Contents/MacOS/launcher.sh"

# Python 代码 → Resources
echo "📋 复制项目文件…"
cp "$PROJECT_DIR/app.py" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/app_gui.py" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/database.py" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/deepseek_client.py" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/vision_client.py" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/requirements.txt" "$APP_BUNDLE/Contents/Resources/"
cp -r "$PROJECT_DIR/templates" "$APP_BUNDLE/Contents/Resources/"
cp -r "$PROJECT_DIR/static" "$APP_BUNDLE/Contents/Resources/"

# ── 图标 ──────────────────────────────────────
echo "🎨 生成图标…"
ICON_ICNS="$SCRIPT_DIR/AppIcon.icns"
if [ -f "$ICON_ICNS" ]; then
    cp "$ICON_ICNS" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
else
    # 尝试用 Python 生成
    echo "   生成图标（需要 Pillow 或 rsvg-convert）…"
    python3 "$SCRIPT_DIR/generate_icon.py"

    # Find the generated icon
    ICON_FILE=$(find "$SCRIPT_DIR" -name "AppIcon.icns" -not -path "*/dist/*" | head -1)
    if [ -n "$ICON_FILE" ] && [ -f "$ICON_FILE" ]; then
        cp "$ICON_FILE" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
    else
        echo "   ⚠️  无法生成图标，跳过（不影响功能）"
    fi
fi

echo "✅ .app 包创建完成: $APP_BUNDLE"

# ── 创建 DMG ──────────────────────────────────
echo ""
echo "💿 创建 DMG…"

DMG_TMP="$DIST_DIR/tmp.dmg"
DMG_VOL="$DIST_DIR/$APP_NAME"

# Create temp DMG
hdiutil create -srcfolder "$APP_BUNDLE" -volname "$APP_NAME" \
    -fs HFS+ -fsargs "-c c=64,a=16,e=16" \
    -format UDRW -size 200M "$DMG_TMP" 2>&1 | tail -1

# Mount it
DEV=$(hdiutil attach -readwrite -noverify -noautoopen "$DMG_TMP" 2>&1 | grep Apple_HFS | awk '{print $1}')
echo "   mounted at /Volumes/$APP_NAME"

# Copy .app and create symlink
sleep 1

# Set folder icon and layout
osascript -e "
tell application \"Finder\"
    tell disk \"$APP_NAME\"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {400, 200, 900, 520}
        set theViewOptions to the icon view options of container window
        set arrangement of theViewOptions to not arranged
        set icon size of theViewOptions to 96
        set background picture of theViewOptions to file \".background:background.png\"
        set position of item \"$APP_NAME.app\" of container window to {150, 155}
        make new alias file at container window to POSIX file \"/Applications\" with properties {name:\"Applications\"}
        set position of item \"Applications\" of container window to {350, 155}
        update without registering applications
        close
    end tell
end tell
" 2>/dev/null || echo "   (Finder 布局跳过)"

# Set custom icon for the volume
if [ -f "$APP_BUNDLE/Contents/Resources/AppIcon.icns" ]; then
    cp "$APP_BUNDLE/Contents/Resources/AppIcon.icns" "/Volumes/$APP_NAME/.VolumeIcon.icns"
    SetFile -a C "/Volumes/$APP_NAME" 2>/dev/null || true
fi

# Unmount
hdiutil detach "$DEV" -force 2>&1 | tail -1

# Convert to compressed, read-only DMG
hdiutil convert "$DMG_TMP" -format UDZO -imagekey zlib-level=9 -o "$DMG_PATH" 2>&1 | tail -1
rm -f "$DMG_TMP"

echo "✅ DMG 已生成: $DMG_PATH"
echo ""
echo "📦 文件大小: $(du -sh "$DMG_PATH" | awk '{print $1}')"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  完成！将 DMG 发送给别人即可安装使用。"
echo ""
echo "  安装方法："
echo "    1. 双击 DMG 挂载"
echo "    2. 拖 「$APP_NAME」 到 Applications 文件夹"
echo "    3. 首次打开若提示「无法验证开发者」："
echo "       右键点击 → 打开 → 仍要打开"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
