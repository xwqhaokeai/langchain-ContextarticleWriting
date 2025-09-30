import uvicorn
from src.api.app import app
from src.config import get_settings
from src.infrastructure.logging import configure_logging

def main():
    settings = get_settings()
    configure_logging(log_level=settings.app.log_level)
    uvicorn.run(
        "src.api.app:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.reload,
        workers=settings.app.workers,
    )

if __name__ == "__main__":
    main()
