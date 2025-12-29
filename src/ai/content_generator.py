import json
import re
from src.ai.gemini_client import GeminiClient
from src.utils.logger import logger


class ContentGenerator:
    """Generador de títulos y descripciones usando Gemini 3 Pro"""

    def __init__(self):
        self.client = GeminiClient()

    def generate_metadata(self, transcript: str, chapters: str = None) -> dict:
        """
        Genera título y descripción basándose en la transcripción

        Args:
            transcript: Transcripción completa del video
            chapters: Capítulos/timestamps opcionales para incluir en la descripción

        Returns:
            Dict con 'title' (≤100 chars) y 'description'

        Raises:
            Exception: Si falla la generación o parsing
        """
        try:
            # Limitar transcripción a ~4000 caracteres para no exceder tokens
            transcript_sample = transcript[:4000]

            logger.info("Generando título y descripción con Gemini...")

            prompt = self._create_metadata_prompt(transcript_sample)

            # No limitar tokens - dejar que Gemini genere lo necesario
            response_text = self.client.generate_text(prompt)

            # Parsear respuesta JSON
            metadata = self._parse_json_response(response_text)

            # Añadir capítulos si están disponibles
            if chapters:
                metadata["description"] = f"{metadata['description']}\n\n⏱️ CAPÍTULOS:\n{chapters}"

            # Validar y ajustar longitudes
            metadata = self._validate_metadata(metadata)

            logger.info(f"Metadata generada:")
            logger.info(f"  Título: {metadata['title']}")
            logger.info(f"  Descripción: {len(metadata['description'])} caracteres")

            return metadata

        except Exception as e:
            logger.error(f"Error generando metadata: {e}", exc_info=True)
            raise

    def _create_metadata_prompt(self, transcript: str) -> str:
        """
        Crea el prompt optimizado para generación de metadata

        Args:
            transcript: Transcripción del video

        Returns:
            Prompt estructurado
        """
        return f"""Analiza esta transcripción de un video de YouTube de un canal TECH/PROGRAMACIÓN y genera metadata atractiva.

TRANSCRIPCIÓN:
{transcript}

INSTRUCCIONES:
1. Crea un TÍTULO atractivo estilo TECH/GEEK:
   - Máximo 100 caracteres
   - Usa terminología tech: API, IA, Cloud, DevOps, Kubernetes, Docker, Python, etc.
   - Incluye emojis tech relevantes: 🚀 💻 🤖 ⚡ 🔥 💡 🎯 ⚙️ 🛠️
   - Estilo clickbait tech pero informativo
   - Puede incluir números o datos específicos si los hay
   - En español pero con términos tech en inglés cuando sea natural
   - Ejemplos de estilo:
     * "🚀 Automatización con IA: Cómo Escalamos 10x con Python y GPT"
     * "💻 Hackathon OpenAI: 48h Programando el Futuro de la IA"
     * "🤖 De Junior a Senior: Las APIs que Cambiarán tu Código"
     * "⚡ Black Friday Tech: Las Ofertas que SÍ Valen para Developers"

2. Crea una DESCRIPCIÓN detallada que incluya:
   - Hook inicial atractivo (1 línea que enganche)
   - Resumen del contenido principal (2-3 párrafos)
   - Puntos clave discutidos (bullet points con emojis)
   - Links placeholder: [LINK] para recursos mencionados
   - 5-8 hashtags tech relevantes al final (#IA #Python #Tech #Programacion etc.)
   - Máximo 500 palabras
   - En español con términos tech en inglés

Responde ÚNICAMENTE con JSON en este formato exacto:
{{
  "title": "Tu título aquí",
  "description": "Tu descripción aquí"
}}

NO incluyas markdown, explicaciones adicionales ni texto fuera del JSON.
"""

    def _parse_json_response(self, response_text: str) -> dict:
        """
        Parsea la respuesta JSON de Gemini

        Args:
            response_text: Texto de respuesta

        Returns:
            Dict con title y description

        Raises:
            ValueError: Si no se puede parsear el JSON
        """
        try:
            # Limpiar markdown code blocks si existen
            cleaned = response_text.strip()

            if cleaned.startswith("```"):
                # Extraer contenido entre ``` markers
                match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)
                else:
                    # Remover el primer y último ```
                    lines = cleaned.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    cleaned = "\n".join(lines)

            # Parsear JSON
            metadata = json.loads(cleaned.strip())

            if "title" not in metadata or "description" not in metadata:
                raise ValueError("JSON no contiene 'title' y 'description'")

            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {e}")
            logger.error(f"Respuesta recibida: {response_text[:500]}...")
            raise ValueError("No se pudo parsear la respuesta como JSON")

    def _validate_metadata(self, metadata: dict) -> dict:
        """
        Valida y ajusta la metadata generada

        Args:
            metadata: Dict con title y description

        Returns:
            Dict validado y ajustado
        """
        # Validar título (máx 100 chars)
        title = metadata.get("title", "").strip()
        if len(title) > 100:
            logger.warning(f"Título muy largo ({len(title)} chars), truncando...")
            title = title[:97] + "..."

        if len(title) < 10:
            logger.warning(f"Título muy corto ({len(title)} chars)")

        # Validar descripción
        description = metadata.get("description", "").strip()
        if len(description) < 50:
            logger.warning(f"Descripción muy corta ({len(description)} chars)")

        return {"title": title, "description": description}

    def generate_title_only(self, transcript: str) -> str:
        """
        Genera solo un título (más rápido)

        Args:
            transcript: Transcripción del video

        Returns:
            Título generado
        """
        try:
            transcript_sample = transcript[:2000]

            prompt = f"""Basándote en esta transcripción de un video de YouTube, genera un título atractivo y descriptivo.

TRANSCRIPCIÓN:
{transcript_sample}

REQUISITOS:
- Máximo 100 caracteres
- Claro y conciso
- En español

Responde SOLO con el título, sin comillas ni explicaciones adicionales.
"""

            # No limitar tokens
            title = self.client.generate_text(prompt)
            title = title.strip().strip('"').strip("'")

            if len(title) > 100:
                title = title[:97] + "..."

            return title

        except Exception as e:
            logger.error(f"Error generando título: {e}", exc_info=True)
            raise
