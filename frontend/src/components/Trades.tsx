import React, { useState, useEffect } from 'react';
import { tradesApi, TradeOffer } from '../api/api';

interface TradesProps {
  accountId: string;
}

type TradeType = 'all' | 'incoming' | 'sent';

export const Trades: React.FC<TradesProps> = ({ accountId }) => {
  const [trades, setTrades] = useState<TradeOffer[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [tradeType, setTradeType] = useState<TradeType>('incoming');

  const loadTrades = async () => {
    if (!accountId) return;
    
    setLoading(true);
    try {
      const response = await tradesApi.getAll(accountId, tradeType);
      setTrades(response.data);
    } catch (error) {
      console.error('Ошибка загрузки трейдов:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrades();
  }, [accountId, tradeType]);

  const handleAction = async (trade: TradeOffer, action: 'accept' | 'decline' | 'cancel') => {
    const tg = (window as any).Telegram.WebApp;
    
    if (tg && tg.showConfirm) {
      const actionText = action === 'accept' ? 'принять' : action === 'decline' ? 'отклонить' : 'отозвать';
      const confirmed = await new Promise<boolean>((resolve) => {
        tg.showConfirm(`Вы действительно хотите ${actionText} этот трейд?`, resolve);
      });
      if (!confirmed) return;
    }

    try {
      await tradesApi.action(accountId, trade.id, trade.partner_id, action);
      setTrades((prev) => prev.filter((t) => t.id !== trade.id));
      
      if (tg && tg.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred('success');
      }
    } catch (error) {
      console.error('Ошибка выполнения операции:', error);
      alert('Ошибка при выполнении операции');
    }
  };

  const getActionButton = (trade: TradeOffer) => {
    if (trade.type === 'incoming') {
      return (
        <div style={styles.actions}>
          <button
            style={styles.acceptButton}
            onClick={() => handleAction(trade, 'accept')}
          >
            ✅ Принять
          </button>
          <button
            style={styles.declineButton}
            onClick={() => handleAction(trade, 'decline')}
          >
            ❌ Отклонить
          </button>
        </div>
      );
    } else if (trade.type === 'sent') {
      return (
        <button
          style={styles.cancelButton}
          onClick={() => handleAction(trade, 'cancel')}
        >
          🔄 Отозвать
        </button>
      );
    }
    return null;
  };

  const formatTime = (timestamp: number) => {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (!accountId) {
    return (
      <div style={styles.container}>
        <p style={styles.empty}>Выберите аккаунт</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>🤝 Трейды</h3>
        <button style={styles.refreshButton} onClick={loadTrades} disabled={loading}>
          🔄
        </button>
      </div>

      <div style={styles.tabs}>
        <button
          style={{
            ...styles.tab,
            backgroundColor: tradeType === 'incoming' ? '#1f538d' : 'transparent',
          }}
          onClick={() => setTradeType('incoming')}
        >
          Входящие
        </button>
        <button
          style={{
            ...styles.tab,
            backgroundColor: tradeType === 'sent' ? '#1f538d' : 'transparent',
          }}
          onClick={() => setTradeType('sent')}
        >
          Отправленные
        </button>
      </div>

      {loading && trades.length === 0 ? (
        <div style={styles.loading}>Загрузка...</div>
      ) : trades.length === 0 ? (
        <div style={styles.empty}>
          {tradeType === 'incoming' ? 'Нет входящих трейдов' : 'Нет отправленных трейдов'}
        </div>
      ) : (
        <div style={styles.list}>
          {trades.map((trade) => (
            <div key={trade.id} style={styles.tradeCard}>
              <div style={styles.tradeHeader}>
                {trade.avatar_url && (
                  <img
                    src={trade.avatar_url}
                    alt="Avatar"
                    style={styles.avatar}
                  />
                )}
                <div style={styles.tradeInfo}>
                  <div style={styles.partnerName}>{trade.partner_name}</div>
                  <div style={styles.tradeTime}>{formatTime(trade.expiration)}</div>
                </div>
              </div>

              <div style={styles.tradeItems}>
                <div style={styles.itemsGive}>
                  <span style={styles.itemsLabel}>Отдаёт:</span>
                  <span style={trade.items_to_give > 0 ? styles.itemsCount : styles.itemsCountZero}>
                    {trade.items_to_give}
                  </span>
                </div>
                <div style={styles.itemsReceive}>
                  <span style={styles.itemsLabel}>Получает:</span>
                  <span style={trade.items_to_receive > 0 ? styles.itemsCount : styles.itemsCountZero}>
                    {trade.items_to_receive}
                  </span>
                </div>
              </div>

              {getActionButton(trade)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    padding: '15px',
    margin: '10px',
    backgroundColor: '#2b2b2b',
    borderRadius: '12px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '15px',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    color: 'white',
  },
  refreshButton: {
    backgroundColor: 'transparent',
    border: 'none',
    color: 'white',
    fontSize: '20px',
    cursor: 'pointer',
    padding: '5px',
  },
  tabs: {
    display: 'flex',
    gap: '10px',
    marginBottom: '15px',
  },
  tab: {
    flex: 1,
    padding: '10px',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
    transition: 'background-color 0.2s',
  },
  loading: {
    textAlign: 'center',
    color: '#888',
    padding: '20px',
  },
  empty: {
    textAlign: 'center',
    color: '#888',
    padding: '20px',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  tradeCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: '8px',
    padding: '12px',
  },
  tradeHeader: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: '10px',
  },
  avatar: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    marginRight: '10px',
  },
  tradeInfo: {
    flex: 1,
  },
  partnerName: {
    fontSize: '14px',
    color: 'white',
    fontWeight: 'bold',
  },
  tradeTime: {
    fontSize: '11px',
    color: '#666',
  },
  tradeItems: {
    display: 'flex',
    justifyContent: 'space-around',
    padding: '10px 0',
    borderTop: '1px solid #333',
    borderBottom: '1px solid #333',
    marginBottom: '10px',
  },
  itemsGive: {
    textAlign: 'center',
  },
  itemsReceive: {
    textAlign: 'center',
  },
  itemsLabel: {
    display: 'block',
    fontSize: '11px',
    color: '#888',
    marginBottom: '4px',
  },
  itemsCount: {
    display: 'block',
    fontSize: '18px',
    color: '#28a745',
    fontWeight: 'bold',
  },
  itemsCountZero: {
    display: 'block',
    fontSize: '18px',
    color: '#dc3545',
    fontWeight: 'bold',
  },
  actions: {
    display: 'flex',
    gap: '8px',
  },
  acceptButton: {
    flex: 1,
    padding: '10px',
    backgroundColor: '#28a745',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 'bold',
  },
  declineButton: {
    flex: 1,
    padding: '10px',
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 'bold',
  },
  cancelButton: {
    width: '100%',
    padding: '10px',
    backgroundColor: '#ffc107',
    color: 'black',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 'bold',
  },
};

export default Trades;
