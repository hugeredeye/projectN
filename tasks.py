from fastapi import BackgroundTasks
from database import db_manager
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def cleanup_task():
    """Периодическая очистка старых файлов"""
    while True:
        try:
            await db_manager.cleanup_old_files()
            logger.info("Cleanup task completed successfully")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
        await asyncio.sleep(86400)  # Запуск раз в день

async def calculate_storage_stats():
    """Расчет статистики хранилища"""
    while True:
        try:
            stats = await db_manager.get_storage_stats()
            logger.info(f"Storage stats: {stats}")
        except Exception as e:
            logger.error(f"Error calculating storage stats: {e}")
        await asyncio.sleep(3600)  # Запуск раз в час 