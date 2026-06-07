import time
import requests
import base64
import rsa
from lib import steam_utils

# Строгие мобильные заголовки
HEADERS = {
    'User-Agent': 'Steam%20Mobile/9039250 CFNetwork/1408.0.4 Darwin/22.5.0)',
    'X-Requested-With': 'com.valvesoftware.android.steam.community',
    'Accept': 'application/json, text/plain, */*'
}

def perform_refresh(username, password, shared_secret):
    """
    Авторизация в Steam с имитацией Android-устройства (Mobile App).
    """
    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        # 1. Получение публичного RSA ключа
        print("-> Шаг 1: Запрос RSA ключа...")
        rsa_req = session.get(
            'https://api.steampowered.com/IAuthenticationService/GetPasswordRSAPublicKey/v1/',
            params={'account_name': username},
            timeout=10
        )
        # Если статус не 200 (ОК), выводим причину и выходим
        if rsa_req.status_code != 200:
            print(f"Ответ Steam (RSA): {rsa_req.status_code} - {rsa_req.text}")
            return None

        rsa_resp = rsa_req.json()['response']
        public_key = rsa.PublicKey(int(rsa_resp['publickey_mod'], 16), int(rsa_resp['publickey_exp'], 16))
        encrypted_pw = base64.b64encode(rsa.encrypt(password.encode('utf-8'), public_key)).decode('utf-8')

        # 2. Инициализация сессии

        print("-> Шаг 2: Инициализация сессии (BeginAuth)...")
        device_id = steam_utils.gen_device_id(username)

        device_details = {
            "device_friendly_name": "Xiaomi Redmi Note 10", # "iPhone 14 Plus"
            "platform_type": "k_EAuthTokenPlatformType_MobileApp",               # k_EAuthTokenPlatformType_iOS
            "os_type": -500,                           # 14
        }

        # 3. Создаем основной запрос
        # В Python параметры передаются как словарь в метод сервиса
        begin_data = {
            # Базовые данные авторизации
            "account_name": username,
            "encrypted_password": encrypted_pw,
            "encryption_timestamp": rsa_resp['timestamp'],
            "persistence": '1',                # 1: Persistent (сохранить сессию), 2: Ephemeral

            # Идентификаторы устройства и платформы
            "website_id": 'Mobile',            # Указываем, что запрос идет от мобильного интерфейса
            "device_friendly_name": "Xiaomi Redmi Note 10", # Имя, которое отобразится в Steam Guard
            "platform_type": 3,      # 64-битный Android (в некоторых библиотеках сюда нужно передавать int: 3 или 9)
            "os_type": -500,                   # Отрицательное значение, характерное для Android

            # Дополнительный параметр для траста (официальное приложение его всегда передает)
            "gaming_device_type": 528
        }


        begin_req = session.post(
            'https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaCredentials/v1/',
            data=begin_data,
            timeout=10
        )

        if begin_req.status_code != 200:
            print(f"Ответ Steam (BeginAuth): {begin_req.status_code} - {begin_req.text}")
            return None

        resp = begin_req.json()['response']
        client_id, request_id, steamid = resp['client_id'], resp['request_id'], resp['steamid']

        # 3. Подтверждение Steam Guard
        print("-> Шаг 3: Отправка Steam Guard...")
        steam_utils.update_offset() # Синхронизация времени
        code = steam_utils.get_guard_code(shared_secret)

        update_req = session.post(
            'https://api.steampowered.com/IAuthenticationService/UpdateAuthSessionWithSteamGuardCode/v1/',
            data={'client_id': client_id, 'steamid': steamid, 'code': code, 'code_type': '3'},
            timeout=10
        )
        if update_req.status_code != 200:
            print(f"Ответ Steam (Guard): {update_req.status_code} - {update_req.text}")
            return None

        # 4. Опрос статуса (Poll)
        print("-> Шаг 4: Ожидание токенов (Poll)...")
        for i in range(12):
            time.sleep(1.5)
            poll_req = session.post(
                'https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1/',
                data={'client_id': client_id, 'request_id': request_id},
                timeout=10
            )

            if poll_req.status_code == 200:
                poll_resp = poll_req.json().get('response', {})
                if poll_resp.get('access_token'):
                    print("-> Успех! Токены получены.")
                    return poll_resp['access_token'], poll_resp['refresh_token']
            else:
                print(f"Ответ Steam (Poll, попытка {i+1}): {poll_req.status_code} - {poll_req.text}")

        print("-> Ошибка: Таймаут ожидания.")
        return None

    except Exception as e:
        print(f"Критическая ошибка скрипта: {e}")
        return None
