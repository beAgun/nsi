from settings import DATABASES
from sqlalchemy import create_engine


DATABASE_CONFIG = DATABASES["b15"]
DATABASE_URI = (f"{DATABASE_CONFIG['engine']}://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}"
                f"@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
                f"?charset={DATABASE_CONFIG['charset']}")
engine = create_engine(DATABASE_URI)

# Таймер, замеряющий время работы функций
USE_TIMER = 0

# Логирование успешных случаев
SUCCESSFUL_LOG = 0