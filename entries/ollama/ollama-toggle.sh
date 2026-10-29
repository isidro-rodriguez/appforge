#!/usr/bin/env bash
# Switcher on/off de Ollama bajo demanda. Se ejecuta como usuario normal.
set -uo pipefail

BASE="${OLLAMA_BASE:-/opt/ollama}"   # sobrescribible solo para tests
BIN="$BASE/bin/ollama"
ICON="$BASE/ollama.png"
LOG="${XDG_STATE_HOME:-$HOME/.local/state}/ollama/serve.log"
PATTERN="$BIN serve"

set -a; . "$BASE/ollama.env"; set +a

notify() { notify-send -a Ollama -i "$ICON" "Ollama" "$1" 2>/dev/null || true; }

if pgrep -u "$USER" -f "$PATTERN" >/dev/null; then
  pkill -u "$USER" -f "$PATTERN"
  notify "Servicio detenido"
  exit 0
fi

mkdir -p "$(dirname "$LOG")"
notify "Arrancando servicio…"
nohup "$BIN" serve >>"$LOG" 2>&1 &

# Espera hasta 15 s a que responda la API
for _ in $(seq 30); do
  if curl -fsS "http://$OLLAMA_HOST/api/version" >/dev/null 2>&1; then
    notify "Servicio activo en $OLLAMA_HOST"
    exit 0
  fi
  sleep 0.5
done
notify "No arrancó. Revisa $LOG"
exit 1
