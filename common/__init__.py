import sys

from loguru import logger
from dotenv import load_dotenv

load_dotenv()

logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | "
                              "<cyan>【{extra[name]}】</cyan> - <level>{message}</level>")
