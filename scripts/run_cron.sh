#!/bin/bash
# =============================================================================
# Script wrapper para ejecutar el procesador de episodios desde cron
#
# USO:
#   Agregar al crontab:
#   */30 * * * * /opt/youtube/scripts/run_cron.sh
#
# El script:
#   1. Cambia al directorio del proyecto
#   2. Activa el entorno virtual
#   3. Ejecuta el procesador para el último video
#   4. Guarda logs con timestamp
# =============================================================================

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/cron.log"
MAX_LOG_SIZE=10485760  # 10MB

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

# Rotar log si es muy grande
if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt $MAX_LOG_SIZE ]; then
    mv "$LOG_FILE" "${LOG_FILE}.$(date +%Y%m%d_%H%M%S).bak"
fi

# Timestamp de inicio
echo "" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "INICIO: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Cambiar al directorio del proyecto
cd "$PROJECT_DIR" || {
    echo "ERROR: No se pudo cambiar al directorio $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

# Activar entorno virtual (soporta tanto venv estándar como uv)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "ADVERTENCIA: No se encontró entorno virtual, usando Python del sistema" >> "$LOG_FILE"
fi

# Verificar que Python está disponible
if ! command -v python &> /dev/null; then
    echo "ERROR: Python no encontrado" >> "$LOG_FILE"
    exit 1
fi

# Ejecutar el procesador
echo "Ejecutando: python procesar_episodio.py --ultimo" >> "$LOG_FILE"
python procesar_episodio.py --ultimo >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# Timestamp de fin
echo "" >> "$LOG_FILE"
echo "FIN: $(date '+%Y-%m-%d %H:%M:%S') - Código de salida: $EXIT_CODE" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Desactivar entorno virtual si se activó
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate 2>/dev/null || true
fi

exit $EXIT_CODE
