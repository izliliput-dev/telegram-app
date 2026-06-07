from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime


class AccountCreate(BaseModel):
    name: str
    mafile_data: Dict[str, Any]
    steam_login: str
    steam_password: str


class AccountResponse(BaseModel):
    id: str
    name: str
    steam_id: str
    has_2fa: bool
    created_at: Optional[datetime] = None


class CodeResponse(BaseModel):
    code: str
    time_remaining: int


class Confirmation(BaseModel):
    id: str
    type: str
    headline: str
    creator_id: str
    account_name: str


class ConfirmationAction(BaseModel):
    confirmation_id: str
    action: str  # 'allow' или 'cancel'


class TradeOffer(BaseModel):
    id: str
    partner_id: str
    partner_name: str
    avatar_url: str
    items_to_give: int
    items_to_receive: int
    expiration: int
    type: str  # 'incoming' или 'sent'


class TradeAction(BaseModel):
    trade_id: str
    partner_id: str
    action: str  # 'accept', 'decline', 'cancel'


class InventoryItem(BaseModel):
    id: str
    name: str
    icon_url: str
    rarity: str
    trade_protected: bool


class AccountLogResponse(BaseModel):
    account_id: str
    name: str
    steam_login: Optional[str]
    steam_password: Optional[str]
    created_at: datetime


class LoginCredentials(BaseModel):
    name: str
    steam_login: str
    steam_password: str
