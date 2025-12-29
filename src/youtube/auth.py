from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource
from config.settings import settings
from src.utils.logger import logger


# Scopes necesarios para el proyecto
SCOPES = [
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.upload",
]


def get_authenticated_service() -> Resource:
    """
    Autentica con YouTube y retorna cliente API

    Flujo:
    - Primera ejecución: abre navegador para autorizar, guarda token
    - Siguientes: usa token guardado, lo refresca automáticamente

    Returns:
        Cliente API de YouTube autenticado

    Raises:
        FileNotFoundError: Si client_secret.json no existe
        Exception: Si falla la autenticación
    """
    credentials = None
    token_path = settings.YOUTUBE_OAUTH_TOKEN

    # Verificar que existe client_secret.json
    if not settings.YOUTUBE_CLIENT_SECRET.exists():
        raise FileNotFoundError(
            f"No se encontró {settings.YOUTUBE_CLIENT_SECRET}. "
            "Descarga las credenciales OAuth2 desde Google Cloud Console."
        )

    # Cargar token existente si disponible
    if token_path.exists():
        logger.info("Cargando token de YouTube existente...")
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # Refrescar o crear nuevo token
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            logger.info("Refrescando token de YouTube...")
            try:
                credentials.refresh(Request())
                logger.info("Token refrescado exitosamente")
            except Exception as e:
                logger.error(f"Error refrescando token: {e}")
                logger.info("Iniciando flujo de autenticación completo...")
                credentials = None

        if not credentials:
            logger.info("Iniciando flujo de autorización OAuth2...")
            logger.info("Se abrirá un navegador para autorizar la aplicación.")

            flow = InstalledAppFlow.from_client_secrets_file(
                str(settings.YOUTUBE_CLIENT_SECRET), SCOPES
            )

            # Ejecutar servidor local para callback OAuth
            # open_browser=True intenta abrir automáticamente, pero si falla mostrará URL
            credentials = flow.run_local_server(
                port=8080,
                prompt="consent",
                open_browser=True,
                success_message="Autenticación exitosa! Puedes cerrar esta ventana."
            )

            logger.info("Autorización completada exitosamente")

        # Guardar token para futuros usos
        settings.ensure_directories()
        token_path.parent.mkdir(parents=True, exist_ok=True)

        with open(token_path, "w") as token:
            token.write(credentials.to_json())

        logger.info(f"Token guardado en {token_path}")

    # Construir servicio de YouTube API
    youtube = build("youtube", "v3", credentials=credentials)
    logger.info("Cliente YouTube API inicializado correctamente")

    return youtube
