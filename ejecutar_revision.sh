#!/bin/bash

# Ruta al directorio donde está LanguageTool
LT_DIR="/root/languagetool/LanguageTool-6.6"

# Ruta al script Python
PY_SCRIPT="/home/ituser/Universidad2026/revisar_trabajos.py"

# Lanzar el servidor de LanguageTool en segundo plano
echo "▶ Iniciando LanguageTool en segundo plano..."
cd "$LT_DIR" || { echo "❌ No se pudo acceder a $LT_DIR"; exit 1; }
java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8010 > /dev/null 2>&1 &
LT_PID=$!

# Esperar hasta que LanguageTool esté disponible (máx 20s)
for i in {1..20}; do
  if curl -s http://localhost:8010/v2/check -o /dev/null; then
    echo "✔️ LanguageTool está listo"
    break
  else
    echo "⏳ Esperando LanguageTool... (${i}s)"
    sleep 1
  fi
done

# Verificar si no respondió a tiempo
if ! curl -s http://localhost:8010/v2/check -o /dev/null; then
  echo "❌ LanguageTool no respondió a tiempo. Abortando."
  kill "$LT_PID" 2>/dev/null
  exit 1
fi

# Ejecutar el script Python desde su propio directorio
echo "▶ Ejecutando revisión automática de trabajos..."
SCRIPT_DIR=$(dirname "$PY_SCRIPT")
cd "$SCRIPT_DIR" || { echo "❌ No se pudo acceder a $SCRIPT_DIR"; kill "$LT_PID"; exit 1; }
python3 "$(basename "$PY_SCRIPT")"

# Finalizar el servidor LanguageTool
echo "▶ Finalizando LanguageTool (PID: $LT_PID)"
kill "$LT_PID" 2>/dev/null

echo "✅ Proceso completo."

