#!/usr/bin/env bash
# Syntax-check the SAGE Lint plugin and deploy it into Sublime Text's Packages folder.
#
# Usage:   bash install.sh
# Env:     SUBLIME_PACKAGES  override the destination Packages directory
#          PYTHON            python interpreter used for the syntax check (default: python)
#
# On first install it writes SageLint.sublime-settings with linter_cwd pre-filled to this
# checkout; on later runs it leaves an existing settings file untouched so your edits stay.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Windows-style path (C:/Users/...) for the settings file, since Python consumes it as cwd.
repo_root="$(cd "$script_dir/../../.." && { pwd -W 2>/dev/null || pwd; })"
python="${PYTHON:-python}"
package_name="SageLint"

# Destination: SUBLIME_PACKAGES if set, else the Sublime Text 4 default under %APPDATA%.
if [ -n "${SUBLIME_PACKAGES:-}" ]; then
  packages_dir="$SUBLIME_PACKAGES"
elif [ -n "${APPDATA:-}" ] && command -v cygpath >/dev/null 2>&1; then
  packages_dir="$(cygpath -u "$APPDATA")/Sublime Text/Packages"
else
  echo "error: cannot locate Sublime Packages folder; set SUBLIME_PACKAGES" >&2
  exit 1
fi
dest="$packages_dir/$package_name"

echo "Checking syntax..."
"$python" - "$script_dir/sage_lint.py" <<'PY'
import ast, sys
ast.parse(open(sys.argv[1], encoding="utf-8").read())
print("ok")
PY

echo "Deploying to $dest"
mkdir -p "$dest"
cp "$script_dir/sage_lint.py" "$dest/"
cp "$script_dir/Default.sublime-commands" "$dest/"
cp "$script_dir/Context.sublime-menu" "$dest/"
cp "$script_dir/SageLint.sublime-syntax" "$dest/"
cp "$script_dir/README.md" "$dest/"
# Pins the package to Sublime's Python 3.8 plugin host (the plugin uses f-strings etc.,
# which the legacy 3.3 host rejects). Must ship with the package.
cp "$script_dir/.python-version" "$dest/"
for keymap in "$script_dir"/*.sublime-keymap; do
  cp "$keymap" "$dest/"
done

settings="$dest/SageLint.sublime-settings"
if [ ! -f "$settings" ]; then
  # Fill linter_cwd with this checkout. Done in Python so the Windows path needs no escaping.
  SRC="$script_dir/SageLint.sublime-settings" DST="$settings" ROOT="$repo_root" "$python" <<'PY'
import os
text = open(os.environ["SRC"], encoding="utf-8").read()
text = text.replace('"linter_cwd": ""', '"linter_cwd": "%s"' % os.environ["ROOT"])
open(os.environ["DST"], "w", encoding="utf-8").write(text)
PY
  echo "Wrote $settings (linter_cwd -> $repo_root)"
else
  echo "Kept existing $settings"
fi

echo "Done. Sublime Text auto-reloads the plugin; restart it if it does not pick up."
