"""
CryptoManager для шифрования данных аккаунтов.
Адаптированная версия из основного проекта.
"""
import json
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Any, Dict


class CryptoManager:
    """Менеджер шифрования данных."""
    
    def __init__(self, encryption_key: str):
        self.encryption_key = encryption_key.encode()
    
    def _derive_key(self, salt: bytes) -> bytes:
        """Получает ключ из пароля с помощью PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.encryption_key))
    
    def encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """Шифрует словарь данных."""
        import os
        salt = os.urandom(16)
        key = self._derive_key(salt)
        fernet = Fernet(key)
        
        json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        encrypted = fernet.encrypt(json_data)
        
        # Возвращаем соль + зашифрованные данные
        return salt + encrypted
    
    def decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Расшифровывает данные."""
        salt = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        key = self._derive_key(salt)
        fernet = Fernet(key)
        
        decrypted = fernet.decrypt(ciphertext)
        return json.loads(decrypted.decode('utf-8'))
    
    def save_encrypted_file(self, path: str, data: Dict[str, Any]) -> None:
        """Сохраняет зашифрованные данные в файл."""
        encrypted = self.encrypt_data(data)
        with open(path, 'wb') as f:
            f.write(encrypted)
    
    def load_encrypted_file(self, path: str) -> Dict[str, Any]:
        """Загружает и расшифровывает данные из файла."""
        with open(path, 'rb') as f:
            encrypted = f.read()
        return self.decrypt_data(encrypted)
    
    def encrypt_single(self, text: str) -> bytes:
        """Шифрует строковое значение."""
        return self.encrypt_data({"value": text})
    
    def decrypt_single(self, encrypted: bytes) -> str:
        """Расшифровывает строковое значение."""
        decrypted = self.decrypt_data(encrypted)
        return decrypted.get("value", "")
