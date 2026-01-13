#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-install}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT_UUID="translator@com.translator.desktop"
APP_ID="com.translator.desktop"

APP_ROOT="${HOME}/.local/share/translator"
APP_DIR="${APP_ROOT}/app"
EXT_DIR="${HOME}/.local/share/gnome-shell/extensions/${EXT_UUID}"
DBUS_DIR="${HOME}/.local/share/dbus-1/services"
DBUS_FILE="${DBUS_DIR}/${APP_ID}.service"

copy_tree() {
  local src="$1"
  local dst="$2"
  if command -v rsync >/dev/null 2>&1; then
    mkdir -p "${dst}"
    rsync -a --delete "${src}/" "${dst}/"
    return
  fi
  rm -rf "${dst}"
  mkdir -p "${dst}"
  cp -a "${src}/." "${dst}/"
}

clean_legacy_keybindings() {
  if ! command -v gsettings >/dev/null 2>&1; then
    return
  fi
  python3 - <<'PY'
import ast
import subprocess

SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
KEY = "custom-keybindings"

try:
    raw = subprocess.check_output(["gsettings", "get", SCHEMA, KEY], text=True).strip()
except Exception:
    raise SystemExit(0)

raw = raw.replace("@as ", "")
try:
    data = ast.literal_eval(raw)
except Exception:
    raise SystemExit(0)

if not isinstance(data, (list, tuple)):
    raise SystemExit(0)

kept: list[str] = []
for path in data:
    if "com_translator_desktop" in path or "translator" in path:
        continue
    kept.append(path)

if kept != list(data):
    subprocess.run(["gsettings", "set", SCHEMA, KEY, str(kept)], check=False)
PY
}

enable_extension() {
  if command -v gsettings >/dev/null 2>&1; then
    gsettings set org.gnome.shell disable-user-extensions false >/dev/null 2>&1 || true
  fi
  if command -v gnome-extensions >/dev/null 2>&1; then
    gnome-extensions enable "${EXT_UUID}" >/dev/null 2>&1 || true
    return
  fi
  if command -v gsettings >/dev/null 2>&1; then
    python3 - <<'PY'
import ast
import subprocess

UUID = "translator@com.translator.desktop"

def _read_list(key: str) -> list[str]:
    try:
        raw = subprocess.check_output(["gsettings", "get", "org.gnome.shell", key], text=True).strip()
    except Exception:
        return []
    raw = raw.replace("@as ", "")
    try:
        data = ast.literal_eval(raw)
    except Exception:
        return []
    if isinstance(data, (list, tuple)):
        return list(data)
    return []

def _write_list(key: str, items: list[str]) -> None:
    subprocess.run(["gsettings", "set", "org.gnome.shell", key, str(items)], check=False)

enabled = _read_list("enabled-extensions")
if UUID not in enabled:
    enabled.append(UUID)
    _write_list("enabled-extensions", enabled)

disabled = _read_list("disabled-extensions")
if UUID in disabled:
    disabled = [item for item in disabled if item != UUID]
    _write_list("disabled-extensions", disabled)
PY
  fi
}

write_dbus_service() {
  mkdir -p "${DBUS_DIR}"
  cat > "${DBUS_FILE}" <<SERVICE
[D-BUS Service]
Name=${APP_ID}
Exec=/usr/bin/env PYTHONPATH=${APP_DIR} /usr/bin/python3 -m desktop_app.main
SERVICE
  chmod 644 "${DBUS_FILE}"
  if command -v gdbus >/dev/null 2>&1; then
    gdbus call --session \
      --dest org.freedesktop.DBus \
      --object-path /org/freedesktop/DBus \
      --method org.freedesktop.DBus.ReloadConfig >/dev/null 2>&1 || true
  fi
}

install_all() {
  copy_tree "${ROOT_DIR}/desktop_app" "${APP_DIR}/desktop_app"
  copy_tree "${ROOT_DIR}/translate_logic" "${APP_DIR}/translate_logic"
  copy_tree "${ROOT_DIR}/icons" "${APP_DIR}/icons"

  copy_tree "${ROOT_DIR}/gnome_extension/${EXT_UUID}" "${EXT_DIR}"
  if command -v glib-compile-schemas >/dev/null 2>&1; then
    glib-compile-schemas "${EXT_DIR}/schemas" >/dev/null 2>&1 || true
  fi

  write_dbus_service
  clean_legacy_keybindings
  enable_extension

  echo "Translator installed. Log out/in if the extension does not appear."
}

remove_all() {
  if command -v gnome-extensions >/dev/null 2>&1; then
    gnome-extensions disable "${EXT_UUID}" >/dev/null 2>&1 || true
  fi
  rm -rf "${EXT_DIR}" "${APP_ROOT}" "${DBUS_FILE}"
  clean_legacy_keybindings
  if command -v gdbus >/dev/null 2>&1; then
    gdbus call --session \
      --dest org.freedesktop.DBus \
      --object-path /org/freedesktop/DBus \
      --method org.freedesktop.DBus.ReloadConfig >/dev/null 2>&1 || true
  fi
  echo "Translator removed."
}

case "${ACTION}" in
  install|update)
    install_all
    ;;
  remove)
    remove_all
    ;;
  *)
    echo "Usage: $0 [install|update|remove]" >&2
    exit 1
    ;;
esac
