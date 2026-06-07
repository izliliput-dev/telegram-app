import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

// Получаем initData сразу при загрузке модуля
const getInitData = () => {
  try {
    const tg = (window as any).Telegram.WebApp;
    return tg?.initData || '';
  } catch {
    return '';
  }
};

// Создаём экземпляр axios
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-Telegram-Init-Data': getInitData(),
  },
});

// Интерфейсы
export interface Account {
  id: string;
  name: string;
  steam_id: string;
  has_2fa: boolean;
  shared_secret?: string;
  identity_secret?: string;
}

export interface CodeResponse {
  code: string;
  time_remaining: number;
}

export interface Confirmation {
  id: string;
  type: string;
  headline: string;
  creator_id: string;
  account_name: string;
}

export interface TradeOffer {
  id: string;
  partner_id: string;
  partner_name: string;
  avatar_url: string;
  items_to_give: number;
  items_to_receive: number;
  expiration: number;
  type: string;
}

export interface AccountLogResponse {
  account_id: string;
  name: string;
  steam_login: string | null;
  steam_password: string | null;
  created_at: string;
}

// API методы
export const accountsApi = {
  getAll: () => api.get<Account[]>('/api/accounts'),
  getById: (id: string) => api.get<Account>(`/api/accounts/${id}`),
  create: (data: { name: string; mafile_data: any; steam_login: string; steam_password: string }) =>
    api.post<Account>('/api/accounts', data),
  delete: (id: string) => api.delete(`/api/accounts/${id}`),
};

export const codeApi = {
  getCode: (accountId: string) => api.get<CodeResponse>(`/api/accounts/${accountId}/code`),
};

export const confirmationsApi = {
  getAll: (accountId: string) => api.get<Confirmation[]>(`/api/accounts/${accountId}/confirmations`),
  action: (accountId: string, confirmationId: string, action: 'allow' | 'cancel') =>
    api.post(`/api/accounts/${accountId}/confirmations/action`, { confirmation_id: confirmationId, action }),
};

export const tradesApi = {
  getAll: (accountId: string, tradeType: 'all' | 'incoming' | 'sent' = 'all') =>
    api.get<TradeOffer[]>(`/api/accounts/${accountId}/trades?trade_type=${tradeType}`),
  action: (accountId: string, tradeId: string, partnerId: string, action: 'accept' | 'decline' | 'cancel') =>
    api.post(`/api/accounts/${accountId}/trades/action`, {
      trade_id: tradeId,
      partner_id: partnerId,
      action,
    }),
  autoAccept: (accountId: string, enable: boolean) =>
    api.post(`/api/accounts/${accountId}/trades/auto-accept?enable=${enable}`),
};

export const timeApi = {
  sync: () => api.get<{ offset: number; server_time: number }>('/api/time-sync'),
};

export const logApi = {
  getMyCreds: () => api.get<AccountLogResponse[]>('/api/accounts/me/creds'),
  logAccount: (data: { name: string; steam_login: string; steam_password: string }) =>
    api.post<AccountLogResponse>('/api/accounts/log', data),
};

export default api;
