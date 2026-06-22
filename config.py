import os
from pathlib import Path
from typing import List, Optional

class Settings:
    def __init__(self):
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
        
        self.bot_token: str = os.getenv("BOT_TOKEN", "")
        self.channel_id: str = os.getenv("CHANNEL_ID", "")
        
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        self.admin_ids: List[int] = []
        if admin_ids_str:
            self.admin_ids = [int(id_.strip()) for id_ in admin_ids_str.split(",") if id_.strip()]
        
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///database/bot.db")
        self.redis_url: Optional[str] = os.getenv("REDIS_URL", None)
        self.use_redis: bool = os.getenv("USE_REDIS", "false").lower() == "true"
        self.backup_interval_hours: int = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
        self.backup_retention_days: int = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))
        self.rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
        self.rate_limit_period_seconds: int = int(os.getenv("RATE_LIMIT_PERIOD_SECONDS", "60"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.log_file: str = os.getenv("LOG_FILE", "logs/bot.log")
        self.maintenance_mode: bool = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
        
        self.base_dir: Path = Path(__file__).parent
        self.database_dir: Path = self.base_dir / "database"
        self.logs_dir: Path = self.base_dir / "logs"
        self.backups_dir: Path = self.base_dir / "backups"
        
        for d in [self.database_dir, self.logs_dir, self.backups_dir]:
            d.mkdir(parents=True, exist_ok=True)

settings = Settings()
