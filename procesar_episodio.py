#!/usr/bin/env python3
"""
🎬 PROCESADOR DE EPISODIOS G33K TEAM
====================================
Script principal para procesar nuevos episodios del podcast.

Operaciones disponibles:
  1. Descargar transcripción (TXT + SRT)
  2. Generar chapters con IA
  3. Generar título optimizado
  4. Generar thumbnail con Gemini 3 Pro
  5. Subir todo a YouTube
  6. Generar resumen para newsletter

USO:
  python procesar_episodio.py <video_id>                    # Procesar todo
  python procesar_episodio.py <video_id> --solo-thumbnail   # Solo thumbnail
  python procesar_episodio.py <video_id> --solo-chapters    # Solo chapters
  python procesar_episodio.py <video_id> --solo-titulo      # Solo título
  python procesar_episodio.py --ultimo                      # Procesar último video del canal
  python procesar_episodio.py --listar                      # Listar videos recientes
  python procesar_episodio.py --newsletter                  # Generar resúmenes newsletter

REQUISITOS:
  - .env con GEMINI_API_KEY
  - data/youtube_token.json con credenciales OAuth
  - Imagen de referencia en data/thumbnails/ut9FDl0vFh4.jpg
"""

import argparse
import json
import re
import sys
import time
import base64
import io
from pathlib import Path
from datetime import datetime

# Importar notificaciones de Telegram
try:
    from src.notifications.telegram import notify_video_processed, notify_error
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# Configuración de rutas
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
CHAPTERS_FILE = DATA_DIR / "chapters_youtube.json"

# Modelos de Gemini
GEMINI_TEXT_MODEL = "models/gemini-2.0-flash"
GEMINI_IMAGE_MODEL = "models/gemini-3-pro-image-preview"

# Imagen de referencia para thumbnails (EP30)
REFERENCE_THUMBNAIL = THUMBNAILS_DIR / "ut9FDl0vFh4.jpg"


def load_env():
    """Carga variables de entorno desde .env"""
    env_path = BASE_DIR / ".env"
    env_vars = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    return env_vars


def get_youtube_client():
    """Obtiene cliente autenticado de YouTube API."""
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials

    token_path = DATA_DIR / 'youtube_token.json'
    with open(token_path, 'r') as f:
        token_data = json.load(f)

    credentials = Credentials(
        token=token_data['token'],
        refresh_token=token_data['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=token_data['client_id'],
        client_secret=token_data['client_secret']
    )

    return build('youtube', 'v3', credentials=credentials)


def get_gemini_client():
    """Configura y retorna cliente de Gemini."""
    import google.generativeai as genai

    env = load_env()
    api_key = env.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY no encontrada en .env")

    genai.configure(api_key=api_key)
    return genai


# =============================================================================
# FUNCIONES DE YOUTUBE
# =============================================================================

def listar_videos_recientes(limit=10):
    """Lista los videos más recientes del canal."""
    youtube = get_youtube_client()

    response = youtube.search().list(
        part='snippet',
        forMine=True,
        type='video',
        order='date',
        maxResults=limit
    ).execute()

    print(f"\n📺 Últimos {limit} videos del canal:")
    print("-" * 70)

    for item in response['items']:
        video_id = item['id']['videoId']
        title = item['snippet']['title'][:50]
        published = item['snippet']['publishedAt'][:10]
        print(f"  {published} | {video_id} | {title}...")

    return response['items']


def obtener_ultimo_video():
    """Obtiene el video más reciente del canal."""
    youtube = get_youtube_client()

    response = youtube.search().list(
        part='snippet',
        forMine=True,
        type='video',
        order='date',
        maxResults=1
    ).execute()

    if response['items']:
        item = response['items'][0]
        return {
            'video_id': item['id']['videoId'],
            'title': item['snippet']['title'],
            'published': item['snippet']['publishedAt']
        }
    return None


def obtener_info_video(video_id):
    """Obtiene información de un video específico."""
    youtube = get_youtube_client()

    response = youtube.videos().list(
        part='snippet,status',
        id=video_id
    ).execute()

    if response['items']:
        item = response['items'][0]
        return {
            'video_id': video_id,
            'title': item['snippet']['title'],
            'description': item['snippet']['description'],
            'published': item['snippet']['publishedAt']
        }
    return None


# =============================================================================
# 1. TRANSCRIPCIÓN
# =============================================================================

def descargar_transcripcion(video_id):
    """Descarga la transcripción de un video en formatos TXT y SRT."""
    from youtube_transcript_api import YouTubeTranscriptApi

    print(f"\n📝 Descargando transcripción para {video_id}...")

    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    ytt_api = YouTubeTranscriptApi()
    transcript_list = ytt_api.list(video_id)

    # Buscar español
    transcript = None
    for t in transcript_list:
        if t.language_code.startswith('es'):
            transcript = t.fetch()
            print(f"  Idioma: {t.language}")
            break

    if not transcript:
        # Usar primera disponible
        transcript = list(transcript_list)[0].fetch()

    # Guardar TXT
    txt_content = ' '.join([entry.text for entry in transcript])
    txt_path = TRANSCRIPTS_DIR / f"{video_id}.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(txt_content)

    # Guardar SRT
    srt_content = ''
    for i, entry in enumerate(transcript, 1):
        start = entry.start
        duration = entry.duration if entry.duration else 2
        end = start + duration

        start_h, start_m = int(start // 3600), int((start % 3600) // 60)
        start_s, start_ms = int(start % 60), int((start % 1) * 1000)
        end_h, end_m = int(end // 3600), int((end % 3600) // 60)
        end_s, end_ms = int(end % 60), int((end % 1) * 1000)

        srt_content += f'{i}\n'
        srt_content += f'{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} --> '
        srt_content += f'{end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}\n'
        srt_content += f'{entry.text}\n\n'

    srt_path = TRANSCRIPTS_DIR / f"{video_id}.srt"
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)

    print(f"  ✅ TXT: {txt_path.name} ({len(txt_content)} chars)")
    print(f"  ✅ SRT: {srt_path.name} ({len(transcript)} segmentos)")

    return txt_path, srt_path


# =============================================================================
# 2. CHAPTERS
# =============================================================================

def generar_chapters(video_id, titulo):
    """Genera chapters usando Gemini."""
    genai = get_gemini_client()

    print(f"\n📑 Generando chapters para {video_id}...")

    # Leer transcripción
    txt_path = TRANSCRIPTS_DIR / f"{video_id}.txt"
    if not txt_path.exists():
        print("  ⚠️ Transcripción no encontrada, descargando...")
        descargar_transcripcion(video_id)

    with open(txt_path, 'r') as f:
        transcript = f.read()

    # Dividir transcripción para cubrir todo el video
    part1 = transcript[:20000]
    part2 = transcript[20000:40000]
    part3 = transcript[40000:]

    prompt = f"""Analiza esta transcripción COMPLETA de un podcast de tecnología (G33K TEAM) y genera capítulos para YouTube.

TÍTULO: {titulo}

PARTE 1 (inicio):
{part1[:6000]}

PARTE 2 (medio):
{part2[:6000]}

PARTE 3 (final):
{part3[:6000]}

Genera 6-8 capítulos que cubran TODO el video en este formato:
0:00 🎙️ Título del capítulo
MM:SS 📱 Otro título
etc.

REGLAS:
- Primer capítulo en 0:00
- Distribuir timestamps a lo largo de todo el video
- Usar emojis relevantes al inicio
- Títulos cortos (máx 40 chars)
- Solo timestamps y títulos, sin explicaciones

CAPÍTULOS:"""

    model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
    response = model.generate_content(prompt)

    chapters = response.text.strip()

    # Limpiar respuesta (quitar texto introductorio si existe)
    lines = chapters.split('\n')
    clean_lines = [l for l in lines if re.match(r'^\d+:\d+', l.strip())]
    chapters = '\n'.join(clean_lines) if clean_lines else chapters

    print(f"  ✅ Chapters generados:")
    for line in chapters.split('\n')[:5]:
        print(f"      {line}")
    if len(chapters.split('\n')) > 5:
        print(f"      ... +{len(chapters.split(chr(10))) - 5} más")

    # Guardar en archivo JSON
    all_chapters = {}
    if CHAPTERS_FILE.exists():
        with open(CHAPTERS_FILE, 'r') as f:
            all_chapters = json.load(f)

    all_chapters[video_id] = chapters

    with open(CHAPTERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_chapters, f, indent=2, ensure_ascii=False)

    return chapters


# =============================================================================
# 3. TÍTULO
# =============================================================================

def generar_titulo(video_id, titulo_actual):
    """Genera un título optimizado usando Gemini."""
    genai = get_gemini_client()

    print(f"\n🏷️ Generando título optimizado...")

    # Leer transcripción
    txt_path = TRANSCRIPTS_DIR / f"{video_id}.txt"
    with open(txt_path, 'r') as f:
        transcript = f.read()[:8000]

    # Extraer número de episodio
    match = re.search(r'S1E(\d+)', titulo_actual)
    episode = int(match.group(1)) if match else 99

    prompt = f"""Analiza esta transcripción y genera un título optimizado para YouTube.

TRANSCRIPCIÓN:
{transcript}

El formato debe ser:
G33K TEAM - S1E{episode} | [Tema Principal]: [Subtema] [2-3 emojis]

Ejemplos:
- G33K TEAM - S1E30 | Black Friday 💸, IA y Get Recall: Tu Inbox Inteligente 🤖
- G33K TEAM - S1E28 | Hackathons, OpenAI en Miami y el Índice Pizza del Pentágono 🍕🤖

REGLAS:
- Máximo 80 caracteres después del "G33K TEAM - S1E{episode} | "
- Destacar temas interesantes/clickbait
- Usar 2-3 emojis relevantes
- Ser descriptivo pero conciso

Genera SOLO el título:"""

    model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
    response = model.generate_content(prompt)

    new_title = response.text.strip()

    # Asegurar formato correcto
    if not new_title.startswith('G33K TEAM'):
        new_title = f"G33K TEAM - S1E{episode} | {new_title}"

    print(f"  ✅ Título: {new_title}")

    return new_title


# =============================================================================
# 4. THUMBNAIL
# =============================================================================

THUMBNAIL_PROMPT = """Generate a YouTube thumbnail image in the EXACT same style as this reference image.

CRITICAL - COPY THIS EXACT STYLE:
- Same 5 cartoon characters at the bottom (bald guy with grey beard and glasses, guy with dark hair and beard in brown shirt, bald guy with glasses and beard in plaid, guy with headphones and beard, slim guy with glasses in black)
- Same warm color palette (beige, brown, orange tones)
- Same cartoon/flat illustration style
- Same layout with monitors/screens in background showing topic keywords

TOPIC FOR THIS EPISODE: "{topic}"
KEYWORDS: {keywords}

REQUIREMENTS:
- Size: 1280x720 pixels (16:9)
- TOP 60%: Tech workspace with 3-5 monitors showing topic-related content:
{monitors_description}
- Add some tech items on desk (keyboards, cables, coffee cup, tablets)
- BOTTOM 40%: The EXACT same 5 characters from reference, same positions, same appearance
- Same beige/brown warm background as reference
- DO NOT add any text overlays for episode number or topic label - just the scene
- Characters should look engaged/interested in the topic

Generate an image that looks like it's from the same series as the reference."""


def generar_thumbnail(video_id, titulo):
    """Genera thumbnail usando Gemini 3 Pro."""
    from PIL import Image, ImageDraw, ImageFont
    genai = get_gemini_client()

    print(f"\n🖼️ Generando thumbnail con {GEMINI_IMAGE_MODEL}...")

    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

    # Extraer tema y keywords del título
    clean = re.sub(r'G33K TEAM - S1E\d+ \| ', '', titulo)
    clean = re.sub(r'[🎙️💻🤯🚀🧠💡♨️🤖📱⚡🎧🛠️⏰🎮🌐🔒💸🍕🦶💾🔄✨👴📉⚠️☁️👨‍💼🏢⚖️💰🔥]', '', clean)

    parts = re.split(r'[:\,]', clean)
    topic = parts[0].strip()[:35] if parts else clean[:35]

    keywords = []
    for part in clean.replace(':', ',').replace('&', ',').replace('+', ',').split(','):
        kw = part.strip()
        if kw and len(kw) > 2:
            keywords.append(kw)
    keywords = keywords[:5]

    # Descripción de monitores
    monitors = []
    positions = ["Left monitor", "Center monitor", "Right monitor"]
    for i, kw in enumerate(keywords[:3]):
        monitors.append(f"  - {positions[i]}: \"{kw.upper()}\" with relevant icon")
    monitors_desc = "\n".join(monitors) if monitors else "  - Monitors showing tech content"

    print(f"  Tema: {topic}")
    print(f"  Keywords: {', '.join(keywords)}")

    # Cargar imagen de referencia
    if not REFERENCE_THUMBNAIL.exists():
        raise FileNotFoundError(f"Imagen de referencia no encontrada: {REFERENCE_THUMBNAIL}")

    reference_img = Image.open(REFERENCE_THUMBNAIL)

    # Generar con Gemini
    prompt = THUMBNAIL_PROMPT.format(
        topic=topic,
        keywords=", ".join(keywords),
        monitors_description=monitors_desc
    )

    model = genai.GenerativeModel(GEMINI_IMAGE_MODEL)
    response = model.generate_content([prompt, reference_img])

    # Extraer imagen de la respuesta
    img = None
    if response.candidates and response.candidates[0].content:
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    image_data = base64.b64decode(image_data)

                img = Image.open(io.BytesIO(image_data))
                img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                print("  ✅ Imagen generada")
                break

    if img is None:
        raise Exception("No se pudo generar la imagen")

    # Añadir textos (episodio y tema)
    img = _añadir_textos_thumbnail(img, titulo, topic)

    # Guardar
    output_path = THUMBNAILS_DIR / f"{video_id}.jpg"
    img.save(output_path, "JPEG", quality=90, optimize=True)

    print(f"  ✅ Guardado: {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")

    return output_path


def _añadir_textos_thumbnail(img, titulo, topic):
    """Añade etiquetas de texto al thumbnail."""
    from PIL import Image, ImageDraw, ImageFont

    # Extraer episodio
    match = re.search(r'S1E(\d+)', titulo)
    episode = int(match.group(1)) if match else 99

    def load_font(size):
        for path in ["/System/Library/Fonts/Supplemental/Impact.ttf",
                     "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]:
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
        return ImageFont.load_default()

    def add_text_outline(draw, text, pos, font, fill, outline, width=3):
        x, y = pos
        for dx in range(-width, width + 1):
            for dy in range(-width, width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline)
        draw.text(pos, text, font=font, fill=fill)

    draw = ImageDraw.Draw(img)
    font_ep = load_font(48)
    font_topic = load_font(36)

    # Episodio (esquina superior derecha)
    ep_text = f"EP {episode:02d}"
    bbox = draw.textbbox((0, 0), ep_text, font=font_ep)
    ep_width = bbox[2] - bbox[0]
    ep_x = 1280 - ep_width - 45
    ep_y = 20

    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [(ep_x - 18, ep_y - 8), (ep_x + ep_width + 18, ep_y + 58)],
        radius=12, fill=(0, 0, 0, 200)
    )
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    add_text_outline(draw, ep_text, (ep_x, ep_y), font_ep, (255, 220, 0), (0, 0, 0), 3)

    # Tema (esquina superior izquierda)
    topic_display = topic[:25]
    bbox = draw.textbbox((0, 0), topic_display, font=font_topic)
    topic_width = bbox[2] - bbox[0]

    overlay2 = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay2_draw = ImageDraw.Draw(overlay2)
    overlay2_draw.rounded_rectangle(
        [(15, 15), (topic_width + 55, 68)],
        radius=10, fill=(255, 140, 0, 230)
    )
    img = Image.alpha_composite(img.convert('RGBA'), overlay2).convert('RGB')
    draw = ImageDraw.Draw(img)
    add_text_outline(draw, topic_display, (32, 22), font_topic, (255, 255, 255), (0, 0, 0), 2)

    return img


# =============================================================================
# 5. SUBIR A YOUTUBE
# =============================================================================

def subir_a_youtube(video_id, titulo=None, chapters=None, thumbnail_path=None):
    """Sube título, descripción con chapters y thumbnail a YouTube."""
    from googleapiclient.http import MediaFileUpload

    youtube = get_youtube_client()

    print(f"\n📤 Subiendo a YouTube ({video_id})...")

    # Obtener video actual
    response = youtube.videos().list(part='snippet', id=video_id).execute()

    if not response['items']:
        raise ValueError(f"Video no encontrado: {video_id}")

    video = response['items'][0]
    snippet = video['snippet']

    # Actualizar título si se proporciona
    if titulo:
        snippet['title'] = titulo
        print(f"  📝 Título: {titulo[:50]}...")

    # Actualizar descripción con chapters
    if chapters:
        # Extraer episodio
        match = re.search(r'S1E(\d+)', snippet['title'])
        episode = int(match.group(1)) if match else 99

        description = f"""⏱️ CAPÍTULOS:
{chapters}

---
🎙️ G33K TEAM - Temporada 1, Episodio {episode}
📺 ¡Suscríbete para más contenido tech!

#G33KTEAM #TechPodcast #Tecnología #IA #Desarrollo
"""
        snippet['description'] = description
        print(f"  📑 Chapters añadidos a descripción")

    # Actualizar video
    youtube.videos().update(
        part='snippet',
        body={'id': video_id, 'snippet': snippet}
    ).execute()
    print(f"  ✅ Video actualizado")

    # Subir thumbnail
    if thumbnail_path and Path(thumbnail_path).exists():
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path), mimetype='image/jpeg')
        ).execute()
        print(f"  ✅ Thumbnail subido")

    print(f"\n🔗 https://youtube.com/watch?v={video_id}")


# =============================================================================
# 6. NEWSLETTER
# =============================================================================

def generar_resumenes_newsletter():
    """Genera resúmenes de todos los episodios para newsletter."""
    genai = get_gemini_client()

    print("\n📰 Generando resúmenes para newsletter...")

    # Obtener todos los videos
    youtube = get_youtube_client()
    all_videos = []
    next_page = None

    while True:
        response = youtube.search().list(
            part='snippet',
            forMine=True,
            type='video',
            order='date',
            maxResults=50,
            pageToken=next_page
        ).execute()

        for item in response['items']:
            title = item['snippet']['title']
            if 'G33K TEAM' in title and 'S1E' in title:
                all_videos.append({
                    'video_id': item['id']['videoId'],
                    'title': title,
                    'published': item['snippet']['publishedAt'][:10]
                })

        next_page = response.get('nextPageToken')
        if not next_page:
            break

    all_videos.sort(key=lambda x: x['published'])

    print(f"  Videos encontrados: {len(all_videos)}")

    model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
    summaries = []

    for i, v in enumerate(all_videos):
        txt_path = TRANSCRIPTS_DIR / f"{v['video_id']}.txt"

        if not txt_path.exists():
            print(f"  [{i+1}/{len(all_videos)}] {v['video_id']} - Sin transcripción")
            continue

        with open(txt_path, 'r') as f:
            transcript = f.read()[:12000]

        prompt = f"""Resume esta transcripción de un podcast de tecnología en español.

TRANSCRIPCIÓN:
{transcript}

Genera un resumen de 2-3 oraciones (máximo 100 palabras) que capture los temas principales.
Solo devuelve el resumen:"""

        try:
            response = model.generate_content(prompt)
            summary = response.text.strip()

            match = re.search(r'S1E(\d+)', v['title'])
            episode = int(match.group(1)) if match else i + 1

            summaries.append({
                "episodio": episode,
                "fecha": v['published'],
                "titulo": v['title'],
                "video_id": v['video_id'],
                "resumen": summary
            })

            print(f"  [{i+1}/{len(all_videos)}] E{episode:02d} ✓")
            time.sleep(1)

        except Exception as e:
            print(f"  [{i+1}/{len(all_videos)}] Error: {e}")

    # Guardar
    output_path = DATA_DIR / "newsletter_summaries.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Guardado: {output_path}")

    return summaries


# =============================================================================
# PROCESAMIENTO COMPLETO
# =============================================================================

def procesar_episodio_completo(video_id):
    """Procesa un episodio completo: transcripción, chapters, título, thumbnail y subida."""

    print("=" * 60)
    print("🎬 PROCESADOR DE EPISODIOS G33K TEAM")
    print("=" * 60)

    # Obtener info del video
    info = obtener_info_video(video_id)
    if not info:
        raise ValueError(f"Video no encontrado: {video_id}")

    titulo_actual = info['title']
    print(f"\n📺 Video: {video_id}")
    print(f"📝 Título actual: {titulo_actual}")
    print(f"📅 Publicado: {info['published'][:10]}")

    # 1. Transcripción
    print("\n" + "=" * 60)
    print("PASO 1/5: TRANSCRIPCIÓN")
    print("=" * 60)
    descargar_transcripcion(video_id)

    # 2. Chapters
    print("\n" + "=" * 60)
    print("PASO 2/5: CHAPTERS")
    print("=" * 60)
    chapters = generar_chapters(video_id, titulo_actual)

    # 3. Título
    print("\n" + "=" * 60)
    print("PASO 3/5: TÍTULO")
    print("=" * 60)
    nuevo_titulo = generar_titulo(video_id, titulo_actual)

    # 4. Thumbnail
    print("\n" + "=" * 60)
    print("PASO 4/5: THUMBNAIL")
    print("=" * 60)
    thumbnail_path = generar_thumbnail(video_id, nuevo_titulo)

    # 5. Subir a YouTube
    print("\n" + "=" * 60)
    print("PASO 5/5: SUBIR A YOUTUBE")
    print("=" * 60)
    subir_a_youtube(video_id, nuevo_titulo, chapters, thumbnail_path)

    print("\n" + "=" * 60)
    print("✅ PROCESAMIENTO COMPLETADO")
    print("=" * 60)
    print(f"🔗 https://youtube.com/watch?v={video_id}")

    # Enviar notificación a Telegram
    if TELEGRAM_AVAILABLE:
        notify_video_processed(video_id, nuevo_titulo, success=True)
        print("📱 Notificación enviada a Telegram")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Procesador de episodios G33K TEAM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python procesar_episodio.py YMCWOLzaIGQ          # Procesar todo
  python procesar_episodio.py --ultimo              # Último video
  python procesar_episodio.py --listar              # Ver videos recientes
  python procesar_episodio.py VIDEO_ID --solo-thumbnail
  python procesar_episodio.py --newsletter          # Generar resúmenes
        """
    )

    parser.add_argument('video_id', nargs='?', help='ID del video de YouTube')
    parser.add_argument('--ultimo', action='store_true', help='Procesar el último video')
    parser.add_argument('--listar', action='store_true', help='Listar videos recientes')
    parser.add_argument('--newsletter', action='store_true', help='Generar resúmenes newsletter')
    parser.add_argument('--solo-transcripcion', action='store_true')
    parser.add_argument('--solo-chapters', action='store_true')
    parser.add_argument('--solo-titulo', action='store_true')
    parser.add_argument('--solo-thumbnail', action='store_true')
    parser.add_argument('--solo-subir', action='store_true')

    args = parser.parse_args()

    try:
        if args.listar:
            listar_videos_recientes()
            return

        if args.newsletter:
            generar_resumenes_newsletter()
            return

        # Obtener video_id
        video_id = args.video_id
        if args.ultimo:
            ultimo = obtener_ultimo_video()
            if ultimo:
                video_id = ultimo['video_id']
                print(f"📺 Último video: {ultimo['title'][:50]}...")
            else:
                print("❌ No se encontró ningún video")
                return

        if not video_id:
            parser.print_help()
            return

        # Obtener info
        info = obtener_info_video(video_id)
        if not info:
            print(f"❌ Video no encontrado: {video_id}")
            return

        titulo = info['title']

        # Operaciones específicas
        if args.solo_transcripcion:
            descargar_transcripcion(video_id)
        elif args.solo_chapters:
            chapters = generar_chapters(video_id, titulo)
            print(f"\n📋 Chapters:\n{chapters}")
        elif args.solo_titulo:
            nuevo = generar_titulo(video_id, titulo)
            print(f"\n🏷️ Nuevo título: {nuevo}")
        elif args.solo_thumbnail:
            generar_thumbnail(video_id, titulo)
        elif args.solo_subir:
            # Cargar chapters si existen
            chapters = None
            if CHAPTERS_FILE.exists():
                with open(CHAPTERS_FILE, 'r') as f:
                    all_chapters = json.load(f)
                chapters = all_chapters.get(video_id)

            thumbnail_path = THUMBNAILS_DIR / f"{video_id}.jpg"
            subir_a_youtube(video_id, None, chapters, thumbnail_path if thumbnail_path.exists() else None)
        else:
            # Procesar todo
            procesar_episodio_completo(video_id)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

        # Notificar error a Telegram
        if TELEGRAM_AVAILABLE:
            notify_error(str(e), context=f"video_id: {video_id if 'video_id' in dir() else 'N/A'}")

        sys.exit(1)


if __name__ == "__main__":
    main()
