"""
Logger setup for Tiki crawling framework.

Provides structured logging with loguru.
"""
import sys
from pathlib import Path
from loguru import logger as loguru_logger
from config.settings import settings


def setup_logger(name: str = "tiki_crawl") -> object:
    """
    Configure logger with file and console output.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if not exists
    settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove default handler
    loguru_logger.remove()
    
    # Add console handler
    loguru_logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
    )
    
    # Add file handler
    loguru_logger.add(
        str(settings.LOG_FILE),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="500 MB",
        retention="7 days",
    )
    
    return loguru_logger


# Create global logger instance
logger = setup_logger()
