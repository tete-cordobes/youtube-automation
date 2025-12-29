# YouTube Automation - G33K TEAM

Sistema de automatización para procesar episodios de YouTube:
- Obtiene transcripciones del audio
- Genera chapters con IA (Gemini)
- Crea títulos optimizados
- Genera thumbnails con estilo G33K TEAM
- Sube todo a YouTube

## Requisitos

- Python 3.11+
- `uv` ([instrucciones](https://github.com/astral-sh/uv))
- YouTube Data API habilitada
- API key de Gemini

## Instalación

```bash
# Instalar dependencias
uv sync

# Configurar credenciales
cp .env.example .env
# Editar .env con tus API keys
```

### Variables de entorno (.env)

```env
YOUTUBE_CHANNEL_ID=UCxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Configurar YouTube OAuth

1. Crea proyecto en [Google Cloud Console](https://console.cloud.google.com/)
2. Habilita YouTube Data API v3
3. Crea credenciales OAuth 2.0 (Aplicación de escritorio)
4. Guarda como `config/client_secret.json`

### Primera autenticación

```bash
uv run python -c "from src.youtube.auth import get_authenticated_service; get_authenticated_service()"
```

## Uso

### Procesar episodio completo

```bash
source .venv/bin/activate
python procesar_episodio.py VIDEO_ID
```

Ejecuta automáticamente:
1. Descarga transcripción (TXT + SRT)
2. Genera chapters con IA
3. Genera título optimizado
4. Genera thumbnail
5. Sube todo a YouTube

### Comandos disponibles

```bash
# Procesar último video del canal
python procesar_episodio.py --ultimo

# Listar videos recientes
python procesar_episodio.py --listar

# Solo transcripción
python procesar_episodio.py VIDEO_ID --solo-transcripcion

# Solo chapters
python procesar_episodio.py VIDEO_ID --solo-chapters

# Solo título
python procesar_episodio.py VIDEO_ID --solo-titulo

# Solo thumbnail
python procesar_episodio.py VIDEO_ID --solo-thumbnail

# Solo subir a YouTube
python procesar_episodio.py VIDEO_ID --solo-subir

# Generar resúmenes para newsletter
python procesar_episodio.py --newsletter
```

### Generar thumbnail G33K TEAM

```bash
python generate_thumbnail_g33k.py VIDEO_ID
python generate_thumbnail_g33k.py VIDEO_ID "G33K TEAM - S1E32 | Título"
```

## Estructura

```
├── procesar_episodio.py         # Script principal
├── generate_thumbnail_g33k.py   # Generador de thumbnails
├── config/
│   ├── settings.py              # Configuración
│   └── thumbnail_style_guide.json
├── src/
│   ├── youtube/                 # API YouTube
│   ├── ai/                      # Generación con Gemini
│   ├── transcription/           # Transcripciones
│   ├── storage/                 # Gestión de archivos
│   ├── notifications/           # Notificaciones
│   └── utils/                   # Utilidades
└── scripts/
    └── run_cron.sh              # Script para cron
```

## Archivos generados (no incluidos en repo)

```
data/
├── transcripts/          # Transcripciones
├── thumbnails/           # Thumbnails generados
├── chapters_youtube.json # Chapters
└── newsletter_summaries.json
```

## Cron

Para ejecutar automáticamente:

```bash
crontab -e
# Agregar:
*/30 * * * * cd /ruta/proyecto && ./scripts/run_cron.sh
```

## Licencia

Uso personal/educativo.
