#!/usr/bin/env python3
"""
Script para generar thumbnails del G33K TEAM con estilo consistente.
Usa Gemini para generar imágenes con los 5 personajes.

GUÍA DE ESTILOS: config/thumbnail_style_guide.json

ESTILO REQUERIDO:
- Tonos marrones/naranjas cálidos (NUNCA azul)
- Logo "G33K TEAM" centrado arriba
- 5 personajes cartoon siempre iguales
- Monitores con contenido temático
- Elementos decorativos según el tema
"""

import json
import re
import base64
import io
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# Configuración
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
METADATA_FILE = DATA_DIR / "all_30_videos_metadata.json"

# Imagen de referencia (usar EP28 como referencia de estilo - tonos marrones correctos)
REFERENCE_IMAGE = THUMBNAILS_DIR / "OvE-UR2q4dY.jpg"

# Dimensiones YouTube thumbnail
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720

# Modelo de Gemini para generación de imágenes
GEMINI_IMAGE_MODEL = "models/gemini-3-pro-image-preview"

# Prompt base para generar thumbnails consistentes
THUMBNAIL_PROMPT_TEMPLATE = """Generate a YouTube thumbnail image in the EXACT same visual style as this reference image.

CRITICAL STYLE ELEMENTS TO COPY EXACTLY:
1. WARM COLOR PALETTE: Beige, brown, orange, tan tones throughout (NOT blue or cold colors)
2. BACKGROUND: Warm brown/tan gradient with tech workspace aesthetic
3. LOGO: "G33K TEAM" text at top center (G33K in dark/black, TEAM in lighter color)
4. TITLE: Large white text with black outline showing the main topic in center
5. MONITORS: 3 computer screens showing topic-related visual content and icons
6. DECORATIVE ELEMENTS: Small icons/objects related to the episode topic (pizzas, trophies, thermometers, etc.)
7. 5 CARTOON CHARACTERS at bottom:
   - Left: Bald guy with gray beard and rectangular glasses
   - Center-left: Dark hair, black beard, big smile, brown/tan shirt
   - Center: Bald with glasses and brown beard, plaid shirt
   - Center-right: Headphones, black beard, dark hoodie
   - Right: Young slim guy with glasses and dark hair

TOPIC FOR THIS EPISODE: "{topic}"
KEYWORDS: {keywords}

REQUIREMENTS:
- Size: 1280x720 pixels (16:9)
- WARM BROWN/ORANGE color scheme like reference (NO blue backgrounds!)
- TOP area: "G33K TEAM" logo centered
- MIDDLE: Large topic title + monitors with topic visuals:
{monitors_description}
- Add decorative elements related to the topic
- BOTTOM 40%: The EXACT same 5 characters from reference in same positions
- Flat/cartoon illustration style matching reference
- DO NOT add "EP XX" badge - I will add that separately

Generate an image that matches the warm brown aesthetic of the reference exactly."""


def load_api_key() -> str:
    """Carga la API key de Gemini."""
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    import os
    return os.getenv("GEMINI_API_KEY", "")


def load_font(size: int):
    """Carga fuente del sistema."""
    font_paths = [
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for font_path in font_paths:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            continue
    return ImageFont.load_default()


def add_text_with_outline(draw, text, position, font, fill_color, outline_color, outline_width=3):
    """Añade texto con borde."""
    x, y = position
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw.text(position, text, font=font, fill=fill_color)


def extract_topic_info(title: str) -> tuple:
    """Extrae tema principal y keywords del título."""
    # Remover prefijo G33K TEAM - S1EXX |
    clean = re.sub(r'G33K TEAM - S1E\d+ \| ', '', title)
    # Remover emojis comunes
    clean = re.sub(r'[🎙️💻🤯🚀🧠💡♨️🤖📱⚡🎧🛠️⏰🎮🌐🔒💸🍕🦶💾🔄✨👴📉⚠️☁️👨‍💼🏢⚖️💰🔥]', '', clean)

    # Tema principal (antes de : o ,)
    parts = re.split(r'[:\,]', clean)
    main_topic = parts[0].strip() if parts else clean

    # Keywords
    keywords = []
    for part in clean.replace(':', ',').replace('&', ',').replace(' y ', ',').replace('+', ',').split(','):
        kw = part.strip()
        if kw and len(kw) > 2:
            keywords.append(kw)

    return main_topic[:35], keywords[:5]


def get_episode_number(title: str) -> int:
    """Extrae número de episodio del título."""
    match = re.search(r'S1E(\d+)', title)
    return int(match.group(1)) if match else 99


def generate_monitors_description(keywords: list) -> str:
    """Genera descripción de monitores basada en keywords."""
    descriptions = []
    positions = ["Left monitor", "Center monitor", "Right monitor", "Far left laptop", "Far right screen"]

    for i, kw in enumerate(keywords[:5]):
        pos = positions[i] if i < len(positions) else f"Monitor {i+1}"
        descriptions.append(f"  - {pos}: \"{kw.upper()}\" with relevant icon")

    if not descriptions:
        descriptions = ["  - Monitors showing tech/podcast related content"]

    return "\n".join(descriptions)


def generate_thumbnail_image(topic: str, keywords: list, reference_img: Image.Image) -> Image.Image:
    """Genera la imagen del thumbnail usando Gemini."""

    monitors_desc = generate_monitors_description(keywords)
    keywords_str = ", ".join(keywords) if keywords else topic

    prompt = THUMBNAIL_PROMPT_TEMPLATE.format(
        topic=topic,
        keywords=keywords_str,
        monitors_description=monitors_desc
    )

    model = genai.GenerativeModel(GEMINI_IMAGE_MODEL)
    response = model.generate_content([prompt, reference_img])

    # Buscar imagen en la respuesta
    if response.candidates and response.candidates[0].content:
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    image_data = base64.b64decode(image_data)

                img = Image.open(io.BytesIO(image_data))
                img = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                return img

    return None


def add_text_overlays(img: Image.Image, episode: int, topic: str) -> Image.Image:
    """Añade las etiquetas de texto (episodio y tema)."""

    draw = ImageDraw.Draw(img)
    font_ep = load_font(48)
    font_topic = load_font(36)

    white = (255, 255, 255)
    black = (0, 0, 0)
    yellow = (255, 220, 0)

    # Número de episodio (esquina superior derecha)
    ep_text = f"EP {episode:02d}"
    bbox = draw.textbbox((0, 0), ep_text, font=font_ep)
    ep_width = bbox[2] - bbox[0]
    ep_x = TARGET_WIDTH - ep_width - 45
    ep_y = 20

    # Fondo negro para episodio
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [(ep_x - 18, ep_y - 8), (ep_x + ep_width + 18, ep_y + 58)],
        radius=12,
        fill=(0, 0, 0, 200)
    )
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    add_text_with_outline(draw, ep_text, (ep_x, ep_y), font_ep, yellow, black, 3)

    # Tema (esquina superior izquierda) - máximo 25 caracteres
    topic_display = topic[:25] if len(topic) > 25 else topic
    bbox = draw.textbbox((0, 0), topic_display, font=font_topic)
    topic_width = bbox[2] - bbox[0]

    # Fondo naranja para tema
    overlay2 = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay2_draw = ImageDraw.Draw(overlay2)
    overlay2_draw.rounded_rectangle(
        [(15, 15), (topic_width + 55, 68)],
        radius=10,
        fill=(255, 140, 0, 230)
    )
    img = Image.alpha_composite(img.convert('RGBA'), overlay2).convert('RGB')
    draw = ImageDraw.Draw(img)
    add_text_with_outline(draw, topic_display, (32, 22), font_topic, white, black, 2)

    return img


def generate_thumbnail(video_id: str, title: str, output_dir: Path = None) -> Path:
    """Genera thumbnail completo para un video."""

    if output_dir is None:
        output_dir = THUMBNAILS_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    # Extraer información del título
    episode = get_episode_number(title)
    topic, keywords = extract_topic_info(title)

    print(f"  Episodio: {episode}")
    print(f"  Tema: {topic}")
    print(f"  Keywords: {', '.join(keywords)}")

    # Cargar imagen de referencia
    if not REFERENCE_IMAGE.exists():
        raise FileNotFoundError(f"No se encontró imagen de referencia: {REFERENCE_IMAGE}")

    reference_img = Image.open(REFERENCE_IMAGE)

    # Generar imagen con Gemini
    print(f"  Generando imagen con {GEMINI_IMAGE_MODEL}...")
    img = generate_thumbnail_image(topic, keywords, reference_img)

    if img is None:
        raise Exception("No se pudo generar la imagen")

    print(f"  Imagen generada correctamente")

    # Añadir textos
    print(f"  Añadiendo etiquetas de texto...")
    img = add_text_overlays(img, episode, topic)

    # Guardar
    output_path = output_dir / f"{video_id}.jpg"
    img.save(output_path, "JPEG", quality=90, optimize=True)

    file_size = output_path.stat().st_size
    print(f"  Guardado: {output_path} ({file_size / 1024:.1f} KB)")

    return output_path


def main():
    """Función principal."""
    print("=" * 60)
    print("GENERADOR DE THUMBNAILS G33K TEAM")
    print(f"Modelo: {GEMINI_IMAGE_MODEL}")
    print("=" * 60)

    # Configurar API
    api_key = load_api_key()
    if not api_key:
        print("ERROR: No se encontró GEMINI_API_KEY")
        sys.exit(1)

    genai.configure(api_key=api_key)

    # Verificar referencia
    if not REFERENCE_IMAGE.exists():
        print(f"ERROR: No se encontró imagen de referencia: {REFERENCE_IMAGE}")
        sys.exit(1)

    # Obtener video_id y título de argumentos o interactivo
    if len(sys.argv) >= 3:
        video_id = sys.argv[1]
        title = sys.argv[2]
    elif len(sys.argv) == 2:
        video_id = sys.argv[1]
        # Buscar título en metadata
        if METADATA_FILE.exists():
            with open(METADATA_FILE, 'r') as f:
                metadata = json.load(f)
            if video_id in metadata:
                title = metadata[video_id].get('title', '')
            else:
                print(f"ERROR: Video {video_id} no encontrado en metadata")
                sys.exit(1)
        else:
            print("ERROR: Proporciona el título como segundo argumento")
            sys.exit(1)
    else:
        print("Uso: python generate_thumbnail_g33k.py <video_id> [titulo]")
        print("Ejemplo: python generate_thumbnail_g33k.py YMCWOLzaIGQ 'G33K TEAM - S1E31 | Mi Título'")
        sys.exit(1)

    print(f"\nVideo ID: {video_id}")
    print(f"Título: {title[:60]}...")
    print("-" * 60)

    try:
        result = generate_thumbnail(video_id, title)
        print("\n" + "=" * 60)
        print(f"✅ Thumbnail generado: {result}")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
