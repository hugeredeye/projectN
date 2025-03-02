import asyncio
from database import Base, engine
import logging

async def init_db():
    logging.basicConfig(level=logging.INFO)
    logging.info("Создание таблиц базы данных...")
    
    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logging.info("База данных успешно инициализирована!")

if __name__ == "__main__":
    asyncio.run(init_db()) 