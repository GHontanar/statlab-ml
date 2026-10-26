#!/bin/sh
# Crea el acceso directo de StatLab en el menú de aplicaciones (solo para este usuario,
# sin permisos de administrador). Ejecutar desde la carpeta descomprimida de StatLab.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$DEST"
sed "s|@STATLAB_DIR@|$DIR|g" "$DIR/statlab.desktop" > "$DEST/statlab.desktop"
chmod +x "$DIR/StatLab" "$DEST/statlab.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DEST" || true
echo "Listo: StatLab aparece en el menú de aplicaciones."
