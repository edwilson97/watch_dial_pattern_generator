#!/bin/bash
# Create and verify the same disk image users open in Finder.
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: bash scripts/package_macos.sh APP DEPENDENCIES OUTPUT.dmg" >&2
  exit 2
fi

app=$1
dependencies=$2
output=$3
staging=$(mktemp -d "${TMPDIR:-/tmp}/watch-dial-package.XXXXXX")
mounted=false
cleanup() {
  if [[ "$mounted" == true ]]; then
    hdiutil detach "$staging/mount" || return
  fi
  rm -rf "$staging"
}
trap cleanup EXIT

mkdir "$staging/contents" "$staging/mount"
ditto "$app" "$staging/contents/WatchDialPatternGenerator.app"
cp "$dependencies" "$staging/contents/dependencies.txt"
ln -s /Applications "$staging/contents/Applications"
hdiutil create -volname "Watch Dial Pattern Generator" -fs HFS+ -format UDZO \
  -srcfolder "$staging/contents" "$output"
hdiutil verify "$output"
hdiutil attach -readonly -nobrowse -mountpoint "$staging/mount" "$output"
mounted=true
test -x "$staging/mount/WatchDialPatternGenerator.app/Contents/MacOS/WatchDialPatternGenerator"
codesign --verify --deep --strict "$staging/mount/WatchDialPatternGenerator.app"
hdiutil detach "$staging/mount"
mounted=false
