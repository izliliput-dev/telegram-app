import os
import hashlib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
STORAGE_DIR = BASE_DIR / os.getenv("STORAGE_PATH", "storage")

# Создаём папки если не существуют
STORAGE_DIR.mkdir(exist_ok=True)
(STORAGE_DIR / "mafiles").mkdir(exist_ok=True)

class Settings:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    WEB_APP_URL: str = os.getenv("WEB_APP_URL", "http://localhost:3000")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "default-key-change-in-production")
    STORAGE_PATH: str = str(STORAGE_DIR)
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Валидация Telegram initData
    def validate_init_data(self, init_data: str) -> bool:
        """Проверяет валидность initData от Telegram"""
        if not init_data or not self.TELEGRAM_BOT_TOKEN:
            return False
        
        try:
            from urllib.parse import parse_qs
            data = parse_qs(init_data)
            
            # Получаем хэш
            received_hash = data.get('hash', [''])[0]
            
            # Формируем строку для проверки (без hash)
            data_check_arr = []
            for key, value in data.items():
                if key != 'hash':
                    data_check_arr.append(f"{key}={value[0]}")
            data_check_arr.sort()
            data_check_string = '\n'.join(data_check_arr)
            
            # Вычисляем секретный ключ
            secret_key = hashlib.sha256(self.TELEGRAM_BOT_TOKEN.encode()).digest()
            
            # Вычисляем хэш
            calculated_hash = hashlib.sha256(
                data_check_string.encode(),
                usedforsecurity=False
            ).hexdigest()
            
            return calculated_hash == received_hash
        except Exception:
            return False

settings = Settings()
