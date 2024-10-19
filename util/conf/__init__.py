from dotenv import find_dotenv, load_dotenv

from .config import Config

load_dotenv(find_dotenv('.env.local'))
load_dotenv()

config = Config()

__all__ = ['config', 'Config']
