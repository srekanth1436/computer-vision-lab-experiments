import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "local-development-key-change-before-publishing",
)

MYSQL_HOST = os.getenv("MYSQL_HOST") or os.getenv("MYSQLHOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT") or os.getenv("MYSQLPORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER") or os.getenv("MYSQLUSER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQLPASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE") or os.getenv(
    "MYSQLDATABASE",
    "smart_attendance",
)

# Local XAMPP may need the database created. Railway already creates it.
_default_create_database = "0" if os.getenv("RAILWAY_ENVIRONMENT") else "1"
MYSQL_CREATE_DATABASE = os.getenv(
    "MYSQL_CREATE_DATABASE",
    _default_create_database,
).lower() in {"1", "true", "yes"}

# Railway volumes expose RAILWAY_VOLUME_MOUNT_PATH automatically.
DATA_ROOT = Path(
    os.getenv("VISIONATTEND_DATA_DIR")
    or os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    or BASE_DIR
).resolve()
