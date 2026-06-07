import React, { useState, useEffect } from 'react';
import { accountsApi, Account } from '../api/api';

interface AccountSwitcherProps {
  onSelectAccount: (account: Account) => void;
  selectedAccount?: Account | null;
  onDeleteAccount?: (accountId: string) => void;
  onAddAccount?: () => void;
}

export const AccountSwitcher: React.FC<AccountSwitcherProps> = ({
  onSelectAccount,
  selectedAccount,
  onDeleteAccount,
  onAddAccount,
}) => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [showDropdown, setShowDropdown] = useState<boolean>(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<boolean>(false);

  // Загрузка списка аккаунтов
  const loadAccounts = async () => {
    try {
      const response = await accountsApi.getAll();
      setAccounts(response.data);
      
      // Если есть аккаунты и не выбран текущий, выбираем первый
      if (response.data.length > 0 && !selectedAccount) {
        onSelectAccount(response.data[0]);
      }
    } catch (error) {
      console.error('Ошибка загрузки аккаунтов:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAccounts();
  }, []);

  // Обновление при изменении selectedAccount извне
  useEffect(() => {
    if (selectedAccount && !accounts.find(a => a.id === selectedAccount.id)) {
      loadAccounts();
    }
  }, [selectedAccount]);

  const handleSelect = (account: Account) => {
    onSelectAccount(account);
    setShowDropdown(false);
    
    // Вибрация через Telegram
    const tg = (window as any).Telegram.WebApp;
    if (tg && tg.HapticFeedback) {
      tg.HapticFeedback.selectionChanged();
    }
  };

  const handleDelete = async (accountId: string) => {
    try {
      await accountsApi.delete(accountId);
      loadAccounts();
      onSelectAccount(null as any);
    } catch (error) {
      console.error('Ошибка удаления:', error);
      alert('Ошибка при удалении аккаунта');
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.buttonRow}>
        <button
          style={styles.button}
          onClick={() => setShowDropdown(!showDropdown)}
        >
          {selectedAccount ? selectedAccount.name : 'Выберите аккаунт'}
          <span style={styles.arrow}>{showDropdown ? '▲' : '▼'}</span>
        </button>
        {onAddAccount && (
          <button
            style={styles.addAccountSmall}
            onClick={onAddAccount}
          >
            +
          </button>
        )}
      </div>

      {showDropdown && (
        <div style={styles.dropdown}>
          {accounts.length === 0 ? (
            <div style={styles.dropdownItem}>Нет аккаунтов</div>
          ) : (
            accounts.map((account) => (
              <div
                key={account.id}
                style={{
                  ...styles.dropdownItem,
                  backgroundColor:
                    selectedAccount?.id === account.id ? '#1f538d' : 'transparent',
                }}
                onClick={() => handleSelect(account)}
              >
                <span style={styles.accountName}>{account.name}</span>
                {account.has_2fa && <span style={styles.badge}>2FA</span>}
                {selectedAccount?.id === account.id && (
                  <button
                    style={styles.deleteButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm(`Удалить аккаунт "${account.name}"?`)) {
                        onDeleteAccount?.(account.id);
                      }
                    }}
                  >
                    🗑️
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    position: 'relative',
    width: '100%',
    marginBottom: '10px',
  },
  buttonRow: {
    display: 'flex',
    gap: '8px',
  },
  button: {
    flex: 1,
    padding: '14px 16px',
    backgroundColor: '#1f538d',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 'bold',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  addAccountSmall: {
    padding: '14px 16px',
    backgroundColor: '#28a745',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '24px',
    fontWeight: 'bold',
    cursor: 'pointer',
    minWidth: '50px',
    lineHeight: 1,
  },
  arrow: {
    fontSize: '12px',
    marginLeft: '8px',
  },
  dropdown: {
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    backgroundColor: '#1a1a1a',
    border: '2px solid #1f538d',
    borderRadius: '8px',
    marginTop: '4px',
    maxHeight: '200px',
    overflowY: 'auto',
    zIndex: 100,
  },
  dropdownItem: {
    padding: '12px 16px',
    color: 'white',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid #333',
  },
  accountName: {
    flex: 1,
    textAlign: 'left',
  },
  badge: {
    backgroundColor: '#28a745',
    color: 'white',
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '10px',
    fontWeight: 'bold',
  },
  deleteButton: {
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    fontSize: '16px',
    padding: '4px 8px',
    marginLeft: '8px',
  },
};

export default AccountSwitcher;
