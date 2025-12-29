# Instrucciones para Claude - YouTube Automation G33K TEAM

## Thumbnails - IMPORTANTE

### Estilo Visual Obligatorio
Los thumbnails del G33K TEAM SIEMPRE deben seguir este estilo:

1. **Colores**: Tonos MARRONES/NARANJAS cálidos (beige, tan, brown)
   - NUNCA usar fondos azules o colores fríos

2. **Logo**: "G33K TEAM" centrado en la parte superior

3. **5 Personajes** (siempre en el mismo orden de izquierda a derecha):
   - Calvo con barba gris y gafas rectangulares
   - Pelo oscuro, barba negra, sonrisa grande, camiseta marrón
   - Calvo con gafas y barba marrón, camisa de cuadros
   - Auriculares, barba negra, sudadera oscura
   - Joven delgado con gafas y pelo oscuro

4. **Elementos**:
   - Monitores mostrando contenido del tema
   - Badge "EP XX" arriba a la derecha
   - Etiqueta naranja con tema arriba a la izquierda
   - Elementos decorativos según el tema

### Archivos Clave
- **Script**: `generate_thumbnail_g33k.py`
- **Guía de estilos**: `config/thumbnail_style_guide.json`
- **Imagen de referencia**: `data/thumbnails/OvE-UR2q4dY.jpg` (EP 28)

### Comando para Generar
```bash
source .venv/bin/activate && python generate_thumbnail_g33k.py <video_id> "<título>"
```

### Comando para Subir a YouTube
```python
from src.youtube.auth import get_authenticated_service
from googleapiclient.http import MediaFileUpload

youtube = get_authenticated_service()
media = MediaFileUpload('data/thumbnails/<video_id>.jpg', mimetype='image/jpeg')
youtube.thumbnails().set(videoId='<video_id>', media_body=media).execute()
```

## Numeración de Episodios

Los episodios van del 1 al 33 (actualmente). El formato del título es:
```
G33K TEAM - S1E{numero} | {tema}
```

## Estructura del Proyecto

```
youtube/
├── config/
│   └── thumbnail_style_guide.json    # Guía de estilos thumbnails
├── data/
│   ├── thumbnails/                   # Thumbnails generados
│   ├── chapters_youtube.json         # Chapters de videos
│   └── all_30_videos_metadata.json   # Metadata de videos
├── src/
│   ├── youtube/                      # API de YouTube
│   └── api/                          # FastAPI backend
├── generate_thumbnail_g33k.py        # Script principal thumbnails
└── .env                              # API keys (GEMINI_API_KEY)
```

## APIs Requeridas

- **GEMINI_API_KEY**: Para generación de imágenes con Gemini
- **YouTube OAuth**: Credenciales en `credentials/` para subir thumbnails
