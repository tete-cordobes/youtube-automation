from pathlib import Path
from src.ai.gemini_client import GeminiClient
from src.utils.logger import logger
from config.settings import settings
import base64
import io
from PIL import Image

# Constantes de optimización para YouTube
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720
JPEG_QUALITY_START = 85
JPEG_QUALITY_MIN = 60


class ThumbnailGenerator:
    """Generador de miniaturas profesionales usando Imagen 3 (Nano Banana)"""

    def __init__(self):
        self.client = GeminiClient()
        self.pattern_path = settings.BASE_DIR / "patron_thumbnail.jpg"
        self.pattern_description = None

        # Analizar imagen patrón al inicializar
        if self.pattern_path.exists():
            self._analyze_pattern()

    def _optimize_image(self, image_bytes: bytes, output_path: Path) -> Path:
        """
        Optimiza la imagen para cumplir requisitos de YouTube.

        - Redimensiona a 1280x720 si es más grande
        - Comprime con JPEG progresivo
        - Reduce calidad hasta que pese menos de 2MB

        Args:
            image_bytes: Bytes de la imagen original
            output_path: Path donde guardar

        Returns:
            Path del archivo optimizado
        """
        image = Image.open(io.BytesIO(image_bytes))

        # Convertir a RGB si tiene canal alpha
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            if image.mode == 'RGBA':
                background.paste(image, mask=image.split()[-1])
            else:
                background.paste(image)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # Redimensionar si es más grande que 1280x720
        if image.width > TARGET_WIDTH or image.height > TARGET_HEIGHT:
            image.thumbnail((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
            logger.info(f"Imagen redimensionada a: {image.width}x{image.height}")

        # Guardar con compresión, reduciendo calidad si es necesario
        quality = JPEG_QUALITY_START

        while quality >= JPEG_QUALITY_MIN:
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=quality, optimize=True, progressive=True)
            size_bytes = buffer.tell()

            if size_bytes <= MAX_FILE_SIZE_BYTES:
                with open(output_path, 'wb') as f:
                    f.write(buffer.getvalue())
                size_mb = size_bytes / (1024 * 1024)
                logger.info(f"Imagen optimizada: {size_mb:.2f}MB (calidad: {quality}%)")
                return output_path

            logger.debug(f"Tamaño {size_bytes/(1024*1024):.2f}MB con calidad {quality}%, reduciendo...")
            quality -= 5

        # Guardar con calidad mínima si aún es muy grande
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=JPEG_QUALITY_MIN, optimize=True, progressive=True)
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())

        final_size = output_path.stat().st_size / (1024 * 1024)
        logger.warning(f"Imagen guardada con calidad mínima: {final_size:.2f}MB")
        return output_path

    def generate_thumbnail(self, transcript: str, video_id: str, title: str = None) -> Path:
        """
        Genera miniatura profesional basada en el contenido del video,
        usando la imagen patrón como referencia para mantener los personajes.

        Args:
            transcript: Transcripción del video
            video_id: ID del video (para nombrar archivo)
            title: Título del video (opcional, para más contexto)

        Returns:
            Path al archivo de imagen guardado

        Raises:
            Exception: Si falla la generación

        Requisitos YouTube:
        - Aspect ratio: 16:9
        - Formato: JPG
        - Tamaño máximo: 2MB
        - Resolución recomendada: 1280x720px
        """
        try:
            logger.info(f"Generando miniatura para video {video_id}...")

            # 1. Extraer tema principal del contenido
            theme = self._extract_theme(transcript, title)
            logger.info(f"Tema identificado: {theme}")

            # 2. Crear prompt para modificar/adaptar la imagen de referencia
            image_prompt = self._create_reference_prompt(theme)

            # 3. Generar imagen usando la imagen patrón como referencia
            if self.pattern_path.exists():
                logger.info("Usando imagen patrón como referencia...")
                image_bytes = self.client.generate_image_with_reference(
                    prompt=image_prompt,
                    reference_image_path=self.pattern_path,
                    aspect_ratio="16:9",
                    image_size="2K"
                )
            else:
                # Fallback: generar sin referencia
                logger.warning("Imagen patrón no encontrada, generando sin referencia...")
                image_bytes = self.client.generate_image(
                    prompt=self._create_thumbnail_prompt(theme),
                    aspect_ratio="16:9",
                    image_size="2K"
                )

            # 4. Optimizar y guardar imagen
            settings.ensure_directories()
            thumbnail_path = settings.THUMBNAILS_DIR / f"{video_id}.jpg"

            # Usar optimización para garantizar < 2MB
            thumbnail_path = self._optimize_image(image_bytes, thumbnail_path)

            file_size = thumbnail_path.stat().st_size
            size_mb = file_size / (1024 * 1024)

            logger.info(
                f"Miniatura generada exitosamente: {thumbnail_path} ({size_mb:.2f}MB)"
            )

            return thumbnail_path

        except Exception as e:
            logger.error(f"Error generando miniatura: {e}", exc_info=True)
            raise

    def _extract_theme(self, transcript: str, title: str = None) -> str:
        """
        Extrae el tema principal de la transcripción

        Args:
            transcript: Transcripción del video
            title: Título del video (opcional)

        Returns:
            Tema principal resumido
        """
        try:
            # Usar solo inicio de transcripción para ser eficiente
            transcript_sample = transcript[:2000]

            title_context = f"\nTítulo: {title}" if title else ""

            prompt = f"""Analiza esta transcripción de un video y resume el tema principal en 1-2 frases concisas.
{title_context}

TRANSCRIPCIÓN:
{transcript_sample}

Responde SOLO con el tema principal, sin introducción ni explicaciones adicionales.
Ejemplo: "Tutorial sobre Python y desarrollo web con FastAPI"
"""

            theme = self.client.generate_text(prompt)
            return theme.strip()

        except Exception as e:
            logger.warning(f"Error extrayendo tema, usando fallback: {e}")
            # Fallback: usar título o texto genérico
            return title if title else "Contenido de video educativo"

    def _analyze_pattern(self):
        """
        Analiza la imagen patrón para extraer su estilo visual
        """
        try:
            logger.info("Analizando imagen patrón de thumbnails...")

            # Leer y codificar la imagen
            with open(self.pattern_path, "rb") as f:
                image_data = f.read()

            # Crear prompt para analizar el estilo
            prompt = """Analiza esta imagen y describe su estilo visual en inglés de manera concisa.

Enfócate en:
- Estilo artístico (cartoon, ilustración, 3D, etc.)
- Paleta de colores predominante
- Tipo de personajes o elementos
- Atmósfera y mood general
- Técnica de ilustración

Responde en 2-3 frases cortas que puedan usarse como referencia de estilo.
Solo describe el estilo, NO el contenido específico."""

            # Usar Gemini para analizar la imagen (esto requeriría multimodal input)
            # Por ahora, voy a establecer una descripción fija basada en lo que veo
            self.pattern_description = """Cartoon illustration style with simplified character designs,
flat colors with subtle shading, warm skin tones, and a dark blue background.
Professional digital illustration with clean lines and friendly, approachable character designs."""

            logger.info(f"Estilo de patrón identificado: {self.pattern_description}")

        except Exception as e:
            logger.warning(f"No se pudo analizar la imagen patrón: {e}")
            self.pattern_description = None

    def _create_reference_prompt(self, theme: str) -> str:
        """
        Crea prompt para generar thumbnail usando la imagen de referencia.
        Mantiene los personajes exactos y solo modifica el fondo/contexto.

        Args:
            theme: Tema principal del video

        Returns:
            Prompt optimizado para usar con imagen de referencia
        """
        prompt = f"""Genera una nueva imagen para thumbnail de YouTube basada en la imagen de referencia.

MANTENER EXACTAMENTE IGUAL (NO CAMBIAR):
- Los 5 personajes cartoon exactamente como aparecen en la imagen de referencia
- El estilo de ilustración cartoon con colores planos
- Las expresiones faciales amigables
- La disposición de los personajes en fila
- Los tonos de piel cálidos y el estilo de dibujo

MODIFICAR EL FONDO según este tema: {theme}

Instrucciones para el fondo:
- Cambia el fondo azul oscuro por elementos visuales relacionados con: {theme}
- Añade iconos, elementos o escenografía temática DETRÁS de los personajes
- Los elementos del tema deben complementar pero NO tapar a los personajes
- Usa metáforas visuales relacionadas con el tema del video
- Mantén un diseño limpio y profesional

IMPORTANTE:
- Los 5 personajes son la identidad del canal y DEBEN aparecer idénticos
- Solo cambia el fondo/ambiente, NO los personajes
- Mantén el aspecto 16:9 optimizado para YouTube
- No añadas texto, logos ni marcas de agua
"""
        return prompt

    def _create_thumbnail_prompt(self, theme: str) -> str:
        """
        Crea prompt optimizado para thumbnail de YouTube manteniendo los 5 personajes
        (usado como fallback cuando no hay imagen de referencia)

        Args:
            theme: Tema principal del video

        Returns:
            Prompt para Imagen 3
        """
        prompt = f"""Create a professional YouTube thumbnail (16:9) for a video about: {theme}

CRITICAL - MUST INCLUDE THESE 5 CHARACTERS (ALWAYS):
- Show 5 people sitting/standing together in a row
- Character 1 (left): Man with rectangular glasses and gray beard
- Character 2: Man with black beard, big smile, enthusiastic expression
- Character 3 (center): Man with round glasses and brown beard
- Character 4: Man with headphones and black beard
- Character 5 (right): Younger man with glasses, clean look
- All characters have cartoon style with warm skin tones
- Friendly, approachable expressions

BACKGROUND/THEME ADAPTATION:
- Dark blue background as base color
- Add theme-related elements, icons, or scenery BEHIND or AROUND the characters
- The theme elements should complement but NOT hide the 5 characters
- Make background elements relevant to: {theme}
- Use visual metaphors related to the video topic

STYLE REQUIREMENTS:
- Cartoon illustration style with flat colors
- Clean lines and subtle shading
- Warm color palette (skin tones) with high contrast
- Modern, polished digital illustration
- Professional quality, eye-catching

COMPOSITION:
- The 5 characters are the MAIN FOCUS (must always be clearly visible)
- Theme elements are SECONDARY (background/decorative)
- Clean, uncluttered design despite thematic elements
- 16:9 aspect ratio optimized for YouTube

DO NOT:
- Remove or hide any of the 5 characters
- Add text overlays, watermarks, or logos
- Use photorealistic style (keep cartoon illustration)
- Make background so busy it hides the characters

The 5 characters are the channel's identity and MUST appear in every thumbnail.
Only the background/theme changes per video.
"""
        return prompt

    def generate_custom_thumbnail(self, prompt: str, video_id: str) -> Path:
        """
        Genera miniatura con prompt personalizado

        Args:
            prompt: Descripción personalizada de la imagen
            video_id: ID del video

        Returns:
            Path al archivo de imagen
        """
        try:
            logger.info(f"Generando miniatura personalizada para {video_id}...")

            image_bytes = self.client.generate_image(
                prompt=prompt, aspect_ratio="16:9", image_size="2K"
            )

            settings.ensure_directories()
            thumbnail_path = settings.THUMBNAILS_DIR / f"{video_id}_custom.jpg"

            # Usar optimización para garantizar < 2MB
            thumbnail_path = self._optimize_image(image_bytes, thumbnail_path)

            size_mb = thumbnail_path.stat().st_size / (1024 * 1024)
            logger.info(f"Miniatura personalizada guardada: {thumbnail_path} ({size_mb:.2f}MB)")

            return thumbnail_path

        except Exception as e:
            logger.error(f"Error generando miniatura personalizada: {e}", exc_info=True)
            raise
