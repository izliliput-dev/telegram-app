import React, { useState, useEffect } from 'react';
import { logApi, AccountLogResponse } from '../api/api';

interface SecretsViewerProps {
  onClose: () => void;
}

const SecretsViewer: React.FC<SecretsViewerProps> = ({ onClose }) => {
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<AccountLogResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSecrets();
  }, []);

  const loadSecrets = async () => {
    try {
      setLoading(true);
      const { data } = await logApi.getMyCreds();
      setAccounts(data || []);
    } catch (err) {
      setError('Ошибка получения данных');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.modal}>
      <div style={styles.modalContent}>
        <h2 style={{ margin: '0 0 20px', fontSize: '20px' }}>📋 Сохраненные аккаунты</h2>
        
        {loading && <p>Загрузка...</p>}
        
        {error && <p style={{ color: '#ff6b6b' }}>{error}</p>}
        
        {accounts.length === 0 && !loading && (
          <p>У вас нет сохраненных аккаунтов.</p>
        )}
        
        {accounts.map((account) => (
          <div key={account.account_id} style={styles.accountItem}>
            <h3 style={{ margin: '0 0 10px', fontSize: '16px' }}>{account.name}</h3>
            {account.steam_login && (
              <p style={{ margin: '5px 0', fontSize: '13px' }}>
                <strong>Логин:</strong> <code style={styles.code}>{account.steam_login}</code>
              </p>
            )}
            {account.steam_password && (
              <p style={{ margin: '5px 0', fontSize: '13px' }}>
                <strong>Пароль:</strong> <code style={styles.code}>{account.steam_password}</code>
              </p>
            )}
          </div>
        ))}
        
        <button style={styles.closeButton} onClick={onClose}>
          Закрыть
        </button>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  modal: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modalContent: {
    backgroundColor: '#1a1a1a',
    padding: '25px',
    borderRadius: '12px',
    maxWidth: '90%',
    maxHeight: '80vh',
    overflowY: 'auto',
  },
  accountItem: {
    backgroundColor: '#2a2a2a',
    padding: '15px',
    borderRadius: '8px',
    marginBottom: '10px',
  },
  code: {
    backgroundColor: '#3a3a3a',
    padding: '3px 8px',
    borderRadius: '4px',
    fontSize: '12px',
  },
  closeButton: {
    marginTop: '20px',
    padding: '12px 24px',
    backgroundColor: '#1f538d',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
    width: '100%',
  },
};

export default SecretsViewer;
