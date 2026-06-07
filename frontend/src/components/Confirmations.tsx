import React, { useState, useEffect } from 'react';
import { confirmationsApi, Confirmation } from '../api/api';

interface ConfirmationsProps {
  accountId: string;
}

const CONF_TYPES: { [key: string]: string } = {
  '1': 'Test',
  '2': 'Trade',
  '3': 'Market',
  '4': 'Opt-Out',
  '5': 'Phone',
  '6': 'Recovery',
};

export const Confirmations: React.FC<ConfirmationsProps> = ({ accountId }) => {
  const [confirmations, setConfirmations] = useState<Confirmation[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const loadConfirmations = async () => {
    if (!accountId) return;

    setLoading(true);
    try {
      const response = await confirmationsApi.getAll(accountId);
      console.log('DEBUG: Получены подтверждения:', response.data);
      setConfirmations(response.data);
    } catch (error: any) {
      console.error('Ошибка загрузки подтверждений:', error);
      console.error('Response:', error.response?.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfirmations();
  }, [accountId]);

  const handleAction = async (confirmationId: string, action: 'allow' | 'cancel') => {
    try {
      await confirmationsApi.action(accountId, confirmationId, action);
      setConfirmations((prev) => prev.filter((c) => c.id !== confirmationId));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(confirmationId);
        return next;
      });
      
      // Вибрация через Telegram
      const tg = (window as any).Telegram.WebApp;
      if (tg && tg.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred('success');
      }
    } catch (error) {
      console.error('Ошибка выполнения операции:', error);
      alert('Ошибка выполнения операции');
    }
  };

  const handleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleMassAction = async (action: 'allow' | 'cancel') => {
    if (selected.size === 0) {
      alert('Ничего не выбрано');
      return;
    }

    const tg = (window as any).Telegram.WebApp;
    if (tg && tg.showConfirm) {
      const confirmed = await new Promise<boolean>((resolve) => {
        tg.showConfirm(
          `Вы действительно хотите ${action === 'allow' ? 'принять' : 'отклонить'} ${selected.size} подтверждений?`,
          resolve
        );
      });
      if (!confirmed) return;
    }

    setLoading(true);
    try {
      for (const id of selected) {
        await confirmationsApi.action(accountId, id, action);
        setConfirmations((prev) => prev.filter((c) => c.id !== id));
      }
      setSelected(new Set());
      
      if (tg && tg.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred('success');
      }
    } catch (error) {
      console.error('Ошибка массового выполнения:', error);
      alert('Ошибка при выполнении операции');
    } finally {
      setLoading(false);
    }
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
        <h3 style={styles.title}>✅ Подтверждения</h3>
        <button style={styles.refreshButton} onClick={loadConfirmations} disabled={loading}>
          🔄
        </button>
      </div>

      {loading && confirmations.length === 0 ? (
        <div style={styles.loading}>Загрузка...</div>
      ) : confirmations.length === 0 ? (
        <div style={styles.empty}>Нет активных подтверждений</div>
      ) : (
        <>
          <div style={styles.list}>
            {confirmations.map((conf) => (
              <div
                key={conf.id}
                style={{
                  ...styles.item,
                  backgroundColor: selected.has(conf.id) ? '#1f538d' : '#2b2b2b',
                }}
                onClick={() => handleSelect(conf.id)}
              >
                <div style={styles.itemInfo}>
                  <div style={styles.itemType}>{CONF_TYPES[conf.type] || '?'}</div>
                  <div style={styles.itemHeadline}>{conf.headline}</div>
                  <div style={styles.itemCreator}>ID: {conf.creator_id.slice(-5)}</div>
                </div>
                <div style={styles.itemActions}>
                  <button
                    style={styles.acceptButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAction(conf.id, 'allow');
                    }}
                  >
                    ✅
                  </button>
                  <button
                    style={styles.declineButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAction(conf.id, 'cancel');
                    }}
                  >
                    ❌
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div style={styles.actionBar}>
            <button
              style={styles.massAcceptButton}
              onClick={() => handleMassAction('allow')}
              disabled={loading}
            >
              ✅ Принять всё
            </button>
            <button
              style={styles.massDeclineButton}
              onClick={() => handleMassAction('cancel')}
              disabled={loading}
            >
              ❌ Отклонить всё
            </button>
          </div>
        </>
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
    maxHeight: '300px',
    overflowY: 'auto',
  },
  item: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    marginBottom: '8px',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  itemInfo: {
    flex: 1,
  },
  itemType: {
    fontSize: '12px',
    color: '#888',
    marginBottom: '4px',
  },
  itemHeadline: {
    fontSize: '14px',
    color: 'white',
    marginBottom: '4px',
  },
  itemCreator: {
    fontSize: '11px',
    color: '#666',
  },
  itemActions: {
    display: 'flex',
    gap: '8px',
  },
  acceptButton: {
    backgroundColor: '#28a745',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 12px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  declineButton: {
    backgroundColor: '#dc3545',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 12px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  actionBar: {
    display: 'flex',
    gap: '10px',
    marginTop: '15px',
  },
  massAcceptButton: {
    flex: 1,
    padding: '12px',
    backgroundColor: '#28a745',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  massDeclineButton: {
    flex: 1,
    padding: '12px',
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 'bold',
    cursor: 'pointer',
  },
};

export default Confirmations;
