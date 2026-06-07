import base64
import hmac
import struct
import time
from hashlib import sha1
from typing import Optional, List, Dict, Any

import requests

# --- КОНСТАНТЫ ---
SYMBOLS = '23456789BCDFGHJKMNPQRTVWXY'
STEAM_API_URL = 'https://api.steampowered.com/ITwoFactorService/QueryTime/v0001'

_current_offset = 0


def update_offset() -> int:
    """Обновляет разницу во времени между локальным ПК и сервером Steam."""
    global _current_offset
    try:
        response = requests.post(STEAM_API_URL, timeout=5)
        response.raise_for_status()
        server_time = int(response.json()['response']['server_time'])
        _current_offset = server_time - int(time.time())
    except (requests.RequestException, KeyError, ValueError):
        _current_offset = 0
    return _current_offset


def gen_device_id(steamid: str) -> str:
    """Генерирует Device ID в формате Android."""
    hash_hex = sha1(str(steamid).encode()).hexdigest()
    return (
        f"android:{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-"
        f"{hash_hex[16:20]}-{hash_hex[20:32]}"
    )


def get_guard_code(shared_secret: str) -> str:
    """Генерирует текущий код Steam Guard."""
    if not shared_secret:
        return "-----"

    current_time = int((time.time() + _current_offset) / 30)
    try:
        secret_bytes = base64.b64decode(shared_secret)
        time_buffer = struct.pack('>Q', current_time)
        hmac_hash = hmac.new(secret_bytes, time_buffer, sha1).digest()

        offset = hmac_hash[19] & 0xF
        full_code = struct.unpack('>I', hmac_hash[offset:offset + 4])[0] & 0x7fffffff

        code = ''
        for _ in range(5):
            code += SYMBOLS[full_code % len(SYMBOLS)]
            full_code //= len(SYMBOLS)
        return code
    except Exception:
        return "ERROR"


def gen_conf_key(secret: str, tag: str, t: Optional[int] = None) -> str:
    """Генерирует ключ подтверждения для запросов к Steam."""
    if t is None:
        t = int(time.time() + _current_offset)

    buf = struct.pack('>Q', t) + tag.encode('ascii')
    hmac_digest = hmac.new(base64.b64decode(secret), buf, sha1).digest()
    return base64.b64encode(hmac_digest).decode()


def get_time_remaining() -> int:
    """Возвращает количество секунд до смены кода."""
    return 30 - (int(time.time() + _current_offset) % 30)


# --- РАБОТА С ПОДТВЕРЖДЕНИЯМИ ---

def fetch_steam_confs(ma_data: Dict[str, Any], time_offset: int) -> List[Dict[str, Any]]:
    """Получает список активных подтверждений из Steam Community."""
    try:
        t = int(time.time() + time_offset)
        sid = str(ma_data['Session']['SteamID'])
        device = ma_data.get('device_id', gen_device_id(sid))
        k = gen_conf_key(ma_data['identity_secret'], 'conf', t)

        params = {
            'p': device,
            'a': sid,
            'k': k,
            't': t,
            'm': 'android',
            'tag': 'conf'
        }

        cookies = {
            'steamLoginSecure': f"{sid}%7C%7C{ma_data['Session']['AccessToken']}"
        }

        url = "https://steamcommunity.com/mobileconf/getlist"
        print(f"DEBUG: Steam URL: {url}")
        print(f"DEBUG: Params: {params}")
        
        r = requests.get(url, params=params, cookies=cookies, timeout=10)
        print(f"DEBUG: Steam Response Status: {r.status_code}")
        print(f"DEBUG: Steam Response: {r.text[:500]}")
        
        r.raise_for_status()
        result = r.json().get('conf', [])
        print(f"DEBUG: Confirmations count: {len(result)}")
        
        return result
    except Exception as e:
        print(f"Ошибка получения подтверждений: {e}")
        return []


def send_steam_op(
    ma_data: Dict[str, Any],
    cid: str,
    ck: str,
    op: str,
    time_offset: int
) -> bool:
    """
    Отправляет команду (allow/cancel) для конкретного подтверждения.
    op: 'allow' (принять) или 'cancel' (отклонить).
    """
    try:
        t = int(time.time() + time_offset)
        # Steam использует 'allow' для подтверждения и 'cancel' для отклонения
        tag = op
        sid = str(ma_data['Session']['SteamID'])
        k = gen_conf_key(ma_data['identity_secret'], tag, t)

        params = {
            'op': op,
            'p': ma_data.get('device_id', gen_device_id(sid)),
            'a': sid,
            'k': k,
            't': t,
            'm': 'android',
            'tag': tag,
            'cid': cid,
            'ck': ck
        }

        cookies = {
            'steamLoginSecure': f"{sid}%7C%7C{ma_data['Session']['AccessToken']}"
        }

        url = "https://steamcommunity.com/mobileconf/ajaxop"
        r = requests.get(url, params=params, cookies=cookies, timeout=10)
        r.raise_for_status()

        return r.json().get('success', False)
    except Exception as e:
        print(f"Ошибка при выполнении операции {op}: {e}")
        return False
