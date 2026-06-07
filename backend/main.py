"""
SDA Telegram App - Backend API
FastAPI приложение для управления аккаунтами Steam
"""
import os
import sys
import json
import time
import uuid
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio

sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from lib.crypto_manager import CryptoManager
from lib import steam_utils
from lib import refresh_account
from lib import trade_manager
from database import AsyncSessionLocal, engine, Base
from models_user import User, Account
from models import (
    AccountCreate, AccountResponse, CodeResponse,
    Confirmation, ConfirmationAction, TradeOffer, TradeAction,
    AccountLogResponse, LoginCredentials
)

# Инициализация крипто менеджера
crypto = CryptoManager(settings.ENCRYPTION_KEY)

# Фоновые задачи авто-принятия
background_tasks: Dict[str, bool] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Создание таблиц БД с помощью асинхронного engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Синхронизация времени
    steam_utils.update_offset()
    yield
    # Очистка ресурсов при остановке
    await engine.dispose()


app = FastAPI(
    title="SDA Telegram App API",
    description="API для управления аккаунтами Steam в Telegram Web App",
    version="1.0.0",
    lifespan=lifespan
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db():
    """Dependency для получения сессии БД."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_telegram_user(
    x_telegram_init_data: str = Header(None, alias="X-Telegram-Init-Data"),
    db=Depends(get_db)
) -> str:
    """Получает или создает пользователя по Telegram ID."""
    import os
    
    if not x_telegram_init_data:
        return "test_user"
    
    # Для локальной разработки пропускаем валидацию
    if os.getenv("SKIP_TELEGRAM_VALIDATION", "false").lower() == "true":
        try:
            from urllib.parse import parse_qs
            data = parse_qs(x_telegram_init_data)
            user_data = data.get('user', [''])[0]
            if user_data:
                user_info = json.loads(user_data)
                return str(user_info.get('id', 'test_user'))
        except Exception:
            pass
        return "test_user"
    
    # Валидация с Telegram
    if settings.validate_init_data(x_telegram_init_data):
        from urllib.parse import parse_qs
        data = parse_qs(x_telegram_init_data)
        user_data = data.get('user', [''])[0]
        if user_data:
            user_info = json.loads(user_data)
            telegram_id = str(user_info.get('id', 'test_user'))
            
            # Создаем пользователя если не существует
            user = await db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                new_user = User(telegram_id=telegram_id)
                db.add(new_user)
                await db.commit()
                await db.refresh(new_user)
            return telegram_id
    
    return "test_user"


# --- API Endpoints ---

@app.get("/")
async def root():
    """Информация об API."""
    return {
        "name": "SDA Telegram App API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/api/accounts", response_model=AccountResponse)
async def create_account(
    account: AccountCreate,
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Добавляет новый аккаунт Steam."""
    account_id = str(uuid.uuid4())
    
    # Пробуем обновить токены сессии
    try:
        tokens = refresh_account.perform_refresh(
            account.steam_login,
            account.steam_password,
            account.mafile_data.get('shared_secret', '')
        )
        if tokens:
            account.mafile_data.setdefault('Session', {})['AccessToken'] = tokens[0]
            account.mafile_data.setdefault('Session', {})['RefreshToken'] = tokens[1]
    except Exception as e:
        print(f"Warning: Could not refresh session: {e}")
    
    # Проверяем пользователя
    user = await db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # Сохраняем данные
    new_account = Account(
        id=account_id,
        user_id=user.id,
        name=account.name,
        mafile_encrypted=crypto.encrypt_data(account.mafile_data),
        steam_login_encrypted=crypto.encrypt_single(account.steam_login),
        steam_password_encrypted=crypto.encrypt_single(account.steam_password),
        steam_id=str(account.mafile_data.get('Session', {}).get('SteamID', '')),
        shared_secret_encrypted=crypto.encrypt_single(account.mafile_data.get('shared_secret', '')),
        identity_secret_encrypted=crypto.encrypt_single(account.mafile_data.get('identity_secret', '')),
        device_id=account.mafile_data.get('device_id', '')
    )
    
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    
    return AccountResponse(
        id=new_account.id,
        name=new_account.name,
        steam_id=new_account.steam_id,
        has_2fa=bool(account.mafile_data.get('shared_secret')),
        created_at=datetime.now()
    )


@app.get("/api/accounts", response_model=List[AccountResponse])
async def get_accounts(
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Получает список всех аккаунтов пользователя."""
    user = await db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        return []
    
    accounts = await db.query(Account).filter(Account.user_id == user.id).all()
    
    result = []
    for acc in accounts:
        result.append(AccountResponse(
            id=acc.id,
            name=acc.name,
            steam_id=acc.steam_id,
            has_2fa=bool(acc.shared_secret_encrypted),
            created_at=acc.created_at
        ))
    
    return result


@app.get("/api/accounts/me")
async def get_my_accounts(
    telegram_user: dict = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Получает список аккаунтов текущего пользователя."""
    telegram_id = slugify_telegram_id(telegram_user)
    return await get_accounts(telegram_id, db)


def slugify_telegram_id(user: dict) -> str:
    """Преобразует user dict в telegram_id."""
    import json
    if isinstance(user, str):
        return user
    user_str = json.dumps(user)
    from urllib.parse import parse_qs
    if 'id' in user:
        return str(user['id'])
    return "test_user"


@app.get("/api/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Получает данные конкретного аккаунта."""
    user = await db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    account = await db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    
    return AccountResponse(
        id=account.id,
        name=account.name,
        steam_id=account.steam_id,
        has_2fa=bool(account.shared_secret_encrypted),
        created_at=account.created_at
    )


@app.delete("/api/accounts/{account_id}")
async def delete_account(
    account_id: str,
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Удаляет аккаунт."""
    user = await db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    account = await db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    
    await db.delete(account)
    await db.commit()
    
    return {"status": "success", "message": "Аккаунт удалён"}


@app.get("/api/accounts/{account_id}/code", response_model=CodeResponse)
async def get_2fa_code(
    account_id: str,
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Генерирует 2FA код для аккаунта."""
    user = await db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    account = await db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    
    shared_secret = crypto.decrypt_single(account.shared_secret_encrypted) if account.shared_secret_encrypted else ''
    code = steam_utils.get_guard_code(shared_secret)
    time_remaining = steam_utils.get_time_remaining()
    
    return CodeResponse(code=code, time_remaining=time_remaining)


@app.get("/api/accounts/{account_id}/confirmations", response_model=List[Confirmation])
async def get_confirmations(
    account_id: str,
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Получает список подтверждений."""
    user = await db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    account = await db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    
    # Расшифровываем maFile
    try:
        ma_data = crypto.decrypt_data(account.mafile_encrypted)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка расшифровки: {e}")
    
    # Получаем подтверждения
    confs = steam_utils.fetch_steam_confs(ma_data, steam_utils._current_offset)
    
    result = []
    for conf in confs:
        result.append(Confirmation(
            id=conf.get('id', ''),
            type=str(conf.get('type', 0)),
            headline=conf.get('headline', ''),
            creator_id=str(conf.get('creator_id', '')),
            account_name=account.name
        ))
    
    return result


@app.post("/api/accounts/{account_id}/confirmations/action")
async def confirmation_action(
    account_id: str,
    action: ConfirmationAction,
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Выполняет действие с подтверждением."""
    user = await db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    account = await db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    
    try:
        ma_data = crypto.decrypt_data(account.mafile_encrypted)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка расшифровки: {e}")
    
    confs = steam_utils.fetch_steam_confs(ma_data, steam_utils._current_offset)
    conf = next((c for c in confs if c.get('id') == action.confirmation_id), None)
    
    if not conf:
        raise HTTPException(status_code=404, detail="Подтверждение не найдено")
    
    success = steam_utils.send_steam_op(
        ma_data,
        action.confirmation_id,
        conf.get('nonce', ''),
        action.action,
        steam_utils._current_offset
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Ошибка выполнения операции")
    
    return {"status": "success", "action": action.action}


@app.get("/api/accounts/{account_id}/trades", response_model=List[TradeOffer])
async def get_trades(
    account_id: str,
    trade_type: str = "all",
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Получает список трейдов."""
    user = await db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    account = await db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    
    try:
        ma_data = crypto.decrypt_data(account.mafile_encrypted)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка расшифровки: {e}")
    
    all_trades = trade_manager.get_all_trades(ma_data)
    result = []
    
    if trade_type in ["all", "incoming"]:
        incoming = trade_manager.get_incoming_trades(
            ma_data, all_trades.get('incoming', []), all_trades.get('descriptions')
        )
        result.extend(incoming)
    
    if trade_type in ["all", "sent"]:
        sent = trade_manager.get_sent_trades(
            ma_data, all_trades.get('sent', []), all_trades.get('descriptions')
        )
        result.extend(sent)
    
    trade_offers = []
    for trade in result:
        trade_offers.append(TradeOffer(
            id=trade['id'],
            partner_id=trade['partner_id'],
            partner_name=trade['sender_name'],
            avatar_url=trade.get('avatar_url', ''),
            items_to_give=trade.get('items_to_give', 0),
            items_to_receive=trade.get('items_to_receive', 0),
            expiration=trade.get('expiration', 0),
            type=trade.get('type', 'incoming')
        ))
    
    return trade_offers


@app.post("/api/accounts/{account_id}/trades/action")
async def trade_action(
    account_id: str,
    action: TradeAction,
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Выполняет действие с трейдом."""
    user = await db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    account = await db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден")
    
    try:
        ma_data = crypto.decrypt_data(account.mafile_encrypted)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка расшифровки: {e}")
    
    success = False
    
    if action.action == "accept":
        success = trade_manager.accept_trade(ma_data, action.trade_id, action.partner_id)
    elif action.action == "decline":
        success = trade_manager.decline_trade(ma_data, action.trade_id)
    elif action.action == "cancel":
        success = trade_manager.cancel_trade(ma_data, action.trade_id)
    else:
        raise HTTPException(status_code=400, detail="Неверноедействие")
    
    if not success:
        raise HTTPException(status_code=500, detail="Ошибка выполнения операции")
    
    return {"status": "success", "action": action.action}


@app.post("/api/accounts/{account_id}/trades/auto-accept")
async def toggle_auto_accept(
    account_id: str,
    enable: bool = True,
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Включает/выключает авто-принятие трейдов."""
    task_key = f"{telegram_id}_{account_id}"
    
    if enable:
        background_tasks[task_key] = True
        threading.Thread(
            target=_auto_accept_worker,
            args=(telegram_id, account_id),
            daemon=True
        ).start()
    else:
        background_tasks[task_key] = False
    
    return {"status": "success", "enabled": enable}


def _auto_accept_worker(telegram_id: str, account_id: str):
    """Фоновый работник для авто-принятия трейдов."""
    task_key = f"{telegram_id}_{account_id}"
    import asyncio
    
    async def run_worker():
        db_session = None
        try:
            from database import AsyncSessionLocal
            while background_tasks.get(task_key, False):
                try:
                    async with AsyncSessionLocal() as session:
                        user = await session.query(User).filter(
                            User.telegram_id == telegram_id).first()
                        if user:
                            account = await session.query(Account).filter(
                                Account.id == account_id,
                                Account.user_id == user.id).first()
                            if account:
                                ma_data = crypto.decrypt_data(account.mafile_encrypted)
                                result = trade_manager.auto_accept_gift_trades(ma_data)
                                if result['accepted'] > 0:
                                    print(f"[Auto-Accept] Принято: {result['accepted']}")
                except Exception as e:
                    print(f"[Auto-Accept] Ошибка: {e}")
                
                for _ in range(60):
                    if not background_tasks.get(task_key, False):
                        break
                    await asyncio.sleep(5)
        finally:
            if db_session:
                await db_session.close()
    
    asyncio.run(run_worker())


@app.get("/api/time-sync")
async def sync_time():
    """Синхронизирует время с сервером Steam."""
    offset = steam_utils.update_offset()
    return {
        "offset": offset,
        "server_time": int(time.time() + offset)
    }


@app.get("/api/accounts/me/creds")
async def get_my_creds(
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Получает сохраненные логины и пароли для всех аккаунтов."""
    user = await db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    accounts = await db.query(Account).filter(Account.user_id == user.id).all()
    
    result = []
    for acc in accounts:
        steam_login = crypto.decrypt_single(acc.steam_login_encrypted) if acc.steam_login_encrypted else None
        steam_password = crypto.decrypt_single(acc.steam_password_encrypted) if acc.steam_password_encrypted else None
        
        result.append(AccountLogResponse(
            account_id=acc.id,
            name=acc.name,
            steam_login=steam_login,
            steam_password=steam_password,
            created_at=acc.created_at
        ))
    
    return result


@app.post("/api/accounts/log")
async def log_account(
    credentials: LoginCredentials,
    telegram_id: str = Depends(get_telegram_user),
    db=Depends(get_db)
):
    """Сохраняет логины/пароли для восстановления."""
    user = await db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        user = User(telegram_id=telegram_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    account_id = str(uuid.uuid4())
    
    new_account = Account(
        id=account_id,
        user_id=user.id,
        name=credentials.name,
        mafile_encrypted=crypto.encrypt_data({}),
        steam_login_encrypted=crypto.encrypt_single(credentials.steam_login),
        steam_password_encrypted=crypto.encrypt_single(credentials.steam_password),
        created_at=datetime.now()
    )
    
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    
    return AccountLogResponse(
        account_id=new_account.id,
        name=new_account.name,
        steam_login=credentials.steam_login,
        steam_password=credentials.steam_password,
        created_at=new_account.created_at
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
