#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${1:-fa-huo-dashboard}"
SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_ROOT"

export PYTHONUTF8=1

python3 -m pip show pyinstaller pywebview >/dev/null

DIST_DIR="$SCRIPT_ROOT/dist"
BUILD_DIR="$SCRIPT_ROOT/build"
RELEASE_ROOT="$SCRIPT_ROOT/release"
RELEASE_DIR="$RELEASE_ROOT/${APP_NAME}-mac"
APP_BUNDLE="$RELEASE_DIR/${APP_NAME}.app"
MACOS_DIR="$APP_BUNDLE/Contents/MacOS"
ICONSET_DIR="$BUILD_DIR/app_icon.iconset"
ICNS_FILE="$BUILD_DIR/app_icon.icns"

rm -rf "$DIST_DIR" "$BUILD_DIR" "$RELEASE_DIR"
mkdir -p "$BUILD_DIR" "$RELEASE_ROOT"

if command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
  mkdir -p "$ICONSET_DIR"
  sips -z 16 16     assets/app_icon.png --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
  sips -z 32 32     assets/app_icon.png --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
  sips -z 32 32     assets/app_icon.png --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
  sips -z 64 64     assets/app_icon.png --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
  sips -z 128 128   assets/app_icon.png --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
  sips -z 256 256   assets/app_icon.png --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
  sips -z 256 256   assets/app_icon.png --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
  sips -z 512 512   assets/app_icon.png --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
  sips -z 512 512   assets/app_icon.png --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
  sips -z 1024 1024 assets/app_icon.png --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null
  iconutil -c icns "$ICONSET_DIR" -o "$ICNS_FILE"
else
  echo "sips/iconutil not found; building without a macOS .icns icon."
  ICNS_FILE=""
fi

PYINSTALLER_ARGS=(
  --noconfirm
  --windowed
  --name "$APP_NAME"
  --hidden-import webview.platforms.cocoa
)

if [[ -n "$ICNS_FILE" ]]; then
  PYINSTALLER_ARGS+=(--icon "$ICNS_FILE")
fi

python3 -m PyInstaller "${PYINSTALLER_ARGS[@]}" desktop_app.py

mkdir -p "$RELEASE_DIR"
cp -R "$DIST_DIR/${APP_NAME}.app" "$APP_BUNDLE"
cp -R "$SCRIPT_ROOT/web" "$MACOS_DIR/web"
cp "$SCRIPT_ROOT/shipment_config.json" "$MACOS_DIR/shipment_config.json"
cp "$SCRIPT_ROOT/assets/app_icon.png" "$MACOS_DIR/app_icon.png"
if [[ ! -f "$MACOS_DIR/app_settings.json" ]]; then
  printf '{}\n' > "$MACOS_DIR/app_settings.json"
fi

mkdir -p "$MACOS_DIR/data" "$MACOS_DIR/uploads" "$MACOS_DIR/reports"
cp "$SCRIPT_ROOT/README.template.txt" "$RELEASE_DIR/README.txt"

(
  cd "$RELEASE_DIR"
  ditto -c -k --keepParent "${APP_NAME}.app" "${APP_NAME}-mac.zip"
)

echo "macOS desktop package created:"
echo "$APP_BUNDLE"
echo "$RELEASE_DIR/${APP_NAME}-mac.zip"
