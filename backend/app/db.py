from sqlalchemy import create_engine

from .config import settings

# Соединение с БД открывается лениво, при первом запросе
engine = create_engine(settings.database_url, pool_pre_ping=True)
