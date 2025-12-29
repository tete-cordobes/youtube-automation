from google import genai
from google.genai import types
from config.settings import settings
from src.utils.logger import logger
from src.utils.retry import gemini_text_limiter, gemini_image_limiter
from PIL import Image
from pathlib import Path


class GeminiClient:
    """Cliente unificado para Gemini 3 Pro (texto) y Nano Banana Pro (imágenes)"""

    def __init__(self):
        """
        Inicializa el cliente con la API key desde settings

        Raises:
            ValueError: Si GEMINI_API_KEY no está configurada
        """
        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY no configurada. "
                "Agregala a .env o variables de entorno."
            )

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info("Cliente Gemini inicializado correctamente")

    @gemini_text_limiter
    def generate_text(self, prompt: str, model: str = None, max_tokens: int = None) -> str:
        """
        Genera texto usando Gemini

        Args:
            prompt: Prompt para el modelo
            model: Modelo a usar (default: settings.GEMINI_TEXT_MODEL)
            max_tokens: Máximo de tokens a generar (opcional)

        Returns:
            Texto generado

        Rate limit: 10 RPM (free tier)
        """
        model = model or settings.GEMINI_TEXT_MODEL

        try:
            logger.debug(f"Generando texto con {model}...")

            config_params = {}
            if max_tokens:
                config_params["max_output_tokens"] = max_tokens

            response = self.client.models.generate_content(
                model=model, contents=prompt, config=types.GenerateContentConfig(**config_params)
            )

            # Extraer texto del response
            if not response.text:
                raise ValueError("Respuesta vacía de Gemini. Puede ser por límite de tokens muy bajo o filtro de seguridad.")

            text = response.text.strip()

            logger.debug(f"Texto generado: {len(text)} caracteres")

            return text

        except Exception as e:
            logger.error(f"Error generando texto: {e}", exc_info=True)
            raise

    @gemini_image_limiter
    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        image_size: str = "2K",
    ) -> bytes:
        """
        Genera imagen usando Gemini 3 Pro Image Preview

        Args:
            prompt: Descripción de la imagen a generar
            aspect_ratio: Relación de aspecto ('16:9', '1:1', '4:3', '9:16')
            image_size: Tamaño de imagen ('2K' para alta calidad)

        Returns:
            Bytes de la imagen generada

        Rate limit: 5 RPM (conservador)
        """
        try:
            model = settings.GEMINI_IMAGE_MODEL
            logger.info(f"Generando imagen con {model} (aspect ratio: {aspect_ratio}, size: {image_size})...")
            logger.debug(f"Prompt: {prompt[:100]}...")

            response = self.client.models.generate_content(
                model=model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=image_size,
                    )
                )
            )

            # Extraer imagen de la respuesta
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    image_bytes = part.inline_data.data
                    logger.info(f"Imagen generada exitosamente: {len(image_bytes)} bytes")
                    return image_bytes

            raise ValueError("No se generó ninguna imagen en la respuesta")

        except Exception as e:
            logger.error(f"Error generando imagen: {e}", exc_info=True)
            raise

    @gemini_image_limiter
    def generate_image_with_reference(
        self,
        prompt: str,
        reference_image_path: Path,
        aspect_ratio: str = "16:9",
        image_size: str = "2K",
    ) -> bytes:
        """
        Genera imagen usando una imagen de referencia para mantener estilo y personajes.

        Args:
            prompt: Descripción de los cambios/tema a aplicar
            reference_image_path: Path a la imagen de referencia
            aspect_ratio: Relación de aspecto ('16:9', '1:1', '4:3', '9:16')
            image_size: Tamaño de imagen ('2K' para alta calidad)

        Returns:
            Bytes de la imagen generada
        """
        try:
            model = settings.GEMINI_IMAGE_MODEL
            logger.info(f"Generando imagen con referencia usando {model}...")
            logger.debug(f"Imagen referencia: {reference_image_path}")
            logger.debug(f"Prompt: {prompt[:100]}...")

            # Cargar imagen de referencia
            reference_image = Image.open(reference_image_path)

            response = self.client.models.generate_content(
                model=model,
                contents=[prompt, reference_image],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=image_size,
                    )
                )
            )

            # Extraer imagen de la respuesta
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    image_bytes = part.inline_data.data
                    logger.info(f"Imagen generada exitosamente: {len(image_bytes)} bytes")
                    return image_bytes

            raise ValueError("No se generó ninguna imagen en la respuesta")

        except Exception as e:
            logger.error(f"Error generando imagen con referencia: {e}", exc_info=True)
            raise

    def count_tokens(self, text: str, model: str = None) -> int:
        """
        Cuenta los tokens en un texto

        Args:
            text: Texto a analizar
            model: Modelo a usar para conteo

        Returns:
            Número de tokens
        """
        model = model or settings.GEMINI_TEXT_MODEL

        try:
            result = self.client.models.count_tokens(model=model, contents=text)

            token_count = result.total_tokens
            logger.debug(f"Token count: {token_count}")

            return token_count

        except Exception as e:
            logger.warning(f"Error contando tokens: {e}")
            # Estimación simple si falla (1 token ≈ 4 caracteres)
            return len(text) // 4
