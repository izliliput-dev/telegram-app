import time
import requests
import re
import binascii
import os

# Глобальный кэш профилей для сессии
_profiles_cache = {}


def _get_session_id():
    """Генерирует случайный sessionid для запросов."""
    return binascii.hexlify(os.urandom(12)).decode()


def is_gift_trade(offer: dict) -> bool:
    """
    Проверяет, является ли трейд подарочным (пользователь ничего не отдаёт).
    """
    items_to_give = offer.get('items_to_give', [])
    return len(items_to_give) == 0


def auto_accept_gift_trades(ma_data: dict) -> dict:
    """
    Автоматически принимает все подарочные трейды.
    """
    result = {'accepted': 0, 'errors': 0, 'total': 0}

    try:
        all_trades = get_all_trades(ma_data)
        incoming = all_trades.get('incoming', [])

        for offer in incoming:
            if offer.get('trade_offer_state') != 2:
                continue

            if is_gift_trade(offer):
                result['total'] += 1
                trade_id = offer.get('tradeofferid')
                partner_id = offer.get('accountid_other')

                print(f"[Auto-Accept] Обнаружен подарочный трейд: {trade_id}")

                if accept_trade(ma_data, trade_id, partner_id):
                    result['accepted'] += 1
                    print(f"[Auto-Accept] ✅ Трейд {trade_id} принят")
                else:
                    result['errors'] += 1
                    print(f"[Auto-Accept] ❌ Ошибка при принятии трейда {trade_id}")

    except Exception as e:
        print(f"[Auto-Accept] Ошибка: {e}")

    return result


def get_all_trades(ma_data: dict) -> dict:
    """
    Получает ВСЕ трейды (входящие и отправленные) ОДНИМ запросом.
    Возвращает dict с ключами 'incoming' и 'sent'.
    """
    try:
        access_token = ma_data.get('Session', {}).get('AccessToken')
        if not access_token:
            return {'incoming': [], 'sent': [], 'descriptions': {}}

        url = "https://api.steampowered.com/IEconService/GetTradeOffers/v1/"
        params = {
            'access_token': access_token,
            'get_received_offers': 1,
            'get_sent_offers': 1,
            'active_only': 1,
            'get_descriptions': 1
        }

        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        offers_received = data.get('response', {}).get('trade_offers_received', [])
        offers_sent = data.get('response', {}).get('trade_offers_sent', [])
        descriptions = data.get('response', {}).get('descriptions', [])

        print(f"[Trade] Загружено: входящих={len(offers_received)}, отправленных={len(offers_sent)}")

        return {
            'incoming': offers_received,
            'sent': offers_sent,
            'descriptions': descriptions
        }
    except Exception as e:
        print(f"[!] Ошибка получения трейдов: {e}")
        return {'incoming': [], 'sent': [], 'descriptions': {}}


def get_incoming_trades(ma_data: dict, raw_offers: list = None, descriptions: dict = None) -> list:
    """
    Возвращает список входящих трейдов.
    """
    if raw_offers is None:
        return []

    access_token = ma_data.get('Session', {}).get('AccessToken')
    return _parse_trade_offers(raw_offers, access_token, "incoming", descriptions)


def get_sent_trades(ma_data: dict, raw_offers: list = None, descriptions: dict = None) -> list:
    """
    Возвращает список отправленных трейдов.
    """
    if raw_offers is None:
        return []

    access_token = ma_data.get('Session', {}).get('AccessToken')
    return _parse_trade_offers(raw_offers, access_token, "sent", descriptions)


def _parse_trade_offers(offers: list, access_token: str, trade_type: str = "incoming", descriptions: dict = None) -> list:
    """
    Парсит список трейдов и добавляет информацию о пользователях.
    """
    if not offers:
        return []

    account_ids = [str(offer['accountid_other']) for offer in offers if 'accountid_other' in offer]
    profiles = _get_player_summaries(access_token, account_ids)

    parsed_offers = []
    seen_ids = set()

    for offer in offers:
        if offer['trade_offer_state'] != 2:
            continue

        offer_id = str(offer['tradeofferid'])
        if offer_id in seen_ids:
            continue
        seen_ids.add(offer_id)

        sender_id = str(offer['accountid_other'])
        sender_info = profiles.get(sender_id, {})

        if trade_type == "sent" and not offer.get('is_our_offer', False):
            continue

        parsed_offers.append({
            'id': offer_id,
            'partner_id': sender_id,
            'partner_id64': str(int(sender_id) + 76561197960265728),
            'sender_name': sender_info.get('personaname', f"ID: {sender_id}"),
            'avatar_url': sender_info.get('avatarfull', sender_info.get('avatarmedium', sender_info.get('avatar', ''))),
            'items_to_receive': len(offer.get('items_to_receive', [])),
            'items_to_give': len(offer.get('items_to_give', [])),
            'message': offer.get('message', ''),
            'expiration': offer.get('expiration_time', 0),
            'type': trade_type,
            '_raw_items_to_receive': offer.get('items_to_receive', []),
            '_raw_items_to_give': offer.get('items_to_give', [])
        })

    print(f"[Trade] {trade_type}: после парсинга {len(parsed_offers)} уникальных трейдов")
    return parsed_offers


def _get_player_summaries(access_token: str, account_ids: list) -> dict:
    """
    Получает аватарки и имена через Steam Community.
    Использует кэширование.
    """
    if not account_ids:
        return {}

    try:
        profiles = {}
        uncached_ids = []
        for aid in set(account_ids):
            if aid in _profiles_cache:
                profiles[aid] = _profiles_cache[aid]
            else:
                uncached_ids.append(aid)

        if not uncached_ids:
            return profiles

        for aid in uncached_ids:
            steamid64 = str(int(aid) + 76561197960265728)
            url = f"https://steamcommunity.com/profiles/{steamid64}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)

            name = f"ID: {aid}"

            name_match = re.search(r'<span class="actual_player_name">([^<]+)</span>', r.text)
            if name_match:
                name = name_match.group(1).strip()

            if name == f"ID: {aid}":
                name_match = re.search(r'"persona_name"\s*:\s*"([^"]+)"', r.text)
                if name_match:
                    name = name_match.group(1).strip()

            if name == f"ID: {aid}":
                og_title = re.search(r'<meta property="og:title" content="([^"]+)"', r.text)
                if og_title:
                    name = og_title.group(1).strip().replace(" on Steam", "").strip()

            if ": " in name:
                name = name.split(": ")[-1]

            avatar_url = ""
            match = re.search(r'<meta property="og:image" content="([^"]+)"', r.text)
            if match:
                avatar_url = match.group(1)

            profile_data = {
                'personaname': name,
                'avatarfull': avatar_url
            }
            profiles[aid] = profile_data
            _profiles_cache[aid] = profile_data

        return profiles
    except Exception as e:
        print(f"[Trade] Ошибка получения аватарок: {e}")
        return {}


def accept_trade(ma_data: dict, trade_id: str, partner_id: str) -> bool:
    """Принимает трейд."""
    try:
        sessionid = _get_session_id()
        sid = str(ma_data['Session']['SteamID'])
        cookies = {
            'steamLoginSecure': f"{sid}%7C%7C{ma_data['Session']['AccessToken']}",
            'sessionid': sessionid
        }

        url = f"https://steamcommunity.com/tradeoffer/{trade_id}/accept"
        headers = {'Referer': f"https://steamcommunity.com/tradeoffer/{trade_id}/"}
        data = {
            'sessionid': sessionid,
            'serverid': '1',
            'tradeofferid': trade_id,
            'partner': partner_id,
            'captcha': ''
        }

        r = requests.post(url, cookies=cookies, headers=headers, data=data, timeout=10)
        resp_data = r.json()
        return r.status_code == 200 and ('tradeid' in resp_data or resp_data.get('needs_mobile_confirmation'))
    except Exception as e:
        print(f"[!] Ошибка принятия трейда {trade_id}: {e}")
        return False


def decline_trade(ma_data: dict, trade_id: str) -> bool:
    """Отклоняет трейд."""
    try:
        sessionid = _get_session_id()
        sid = str(ma_data['Session']['SteamID'])
        cookies = {
            'steamLoginSecure': f"{sid}%7C%7C{ma_data['Session']['AccessToken']}",
            'sessionid': sessionid
        }

        url = f"https://steamcommunity.com/tradeoffer/{trade_id}/decline"
        data = {'sessionid': sessionid}

        r = requests.post(url, cookies=cookies, data=data, timeout=10)
        return r.json().get('tradeofferid') == trade_id
    except Exception as e:
        print(f"[!] Ошибка отклонения трейда {trade_id}: {e}")
        return False


def cancel_trade(ma_data: dict, trade_id: str) -> bool:
    """Отзывает отправленный трейд."""
    try:
        sessionid = _get_session_id()
        sid = str(ma_data['Session']['SteamID'])
        cookies = {
            'steamLoginSecure': f"{sid}%7C%7C{ma_data['Session']['AccessToken']}",
            'sessionid': sessionid
        }

        url = f"https://steamcommunity.com/tradeoffer/{trade_id}/cancel"
        data = {'sessionid': sessionid}

        r = requests.post(url, cookies=cookies, data=data, timeout=10)
        return r.json().get('tradeofferid') == trade_id
    except Exception as e:
        print(f"[!] Ошибка отзыва трейда {trade_id}: {e}")
        return False


def get_trade_url(ma_data: dict) -> str:
    """Парсит страницу приватности для получения ссылки на обмен."""
    try:
        sid = str(ma_data['Session']['SteamID'])
        cookies = {'steamLoginSecure': f"{sid}%7C%7C{ma_data['Session']['AccessToken']}"}

        url = f"https://steamcommunity.com/profiles/{sid}/tradeoffers/privacy"
        r = requests.get(url, cookies=cookies, timeout=10)

        match = re.search(r'id="trade_offer_access_url"\s+value="(https://steamcommunity\.com/tradeoffer/new/\?partner=\d+&token=[^"]+)"', r.text)
        if match:
            return match.group(1)
        return "Не удалось найти ссылку."
    except Exception as e:
        print(f"[!] Ошибка получения Trade URL: {e}")
        return "Ошибка соединения."
