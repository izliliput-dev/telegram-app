import React, { useState, useEffect } from 'react';
import WebApp from '@twa-dev/sdk';
import { Account } from './api/api';
import { AccountSwitcher } from './components/AccountSwitcher';
import { CodeGenerator } from './components/CodeGenerator';
import { Confirmations } from './components/Confirmations';
import { Trades } from './components/Trades';
import { AddAccount } from './components/AddAccount';
import { updateTimeOffset } from './utils/steamGuard';

type Tab = 'codes' | 'confirmations' | 'trades';

const App: React.FC = () => {
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('codes');
  const [showAddAccount, setShowAddAccount] = useState<boolean>(false);
  const [accountsKey, setAccountsKey] = useState<number>(0);

  // Инициализация Telegram WebApp
  useEffect(() => {
    const tg = WebApp;
    tg.ready();
    tg.expand();

    // Важно: ждём пока initData станет доступен
    tg.ready();

    console.log('Telegram WebApp initialized');
    console.log('initData:', tg.initData ? tg.initData.substring(0, 50) + '...' : 'empty');
    console.log('initDataUnsafe:', tg.initDataUnsafe);

    // Настройка цветов под тему Telegram
    if (tg.themeParams) {
      document.body.style.backgroundColor = tg.themeParams.bg_color || '#0e0e0e';
      document.body.style.color = tg.themeParams.text_color || '#ffffff';
    }

    // Синхронизация времени
    updateTimeOffset();
  }, []);

  const handleSelectAccount = (account: Account) => {
    setSelectedAccount(account);
  };

  const handleAccountAdded = () => {
    // Обновляем список аккаунтов
    setAccountsKey(prev => prev + 1);
    setSelectedAccount(null);
  };

  const handleAccountDeleted = (accountId: string) => {
    if (selectedAccount?.id === accountId) {
      setSelectedAccount(null);
    }
    setAccountsKey(prev => prev + 1);
  };

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.title}>🛡️ SDA Telegram</h1>
        <div style={styles.userInfo}>
          {WebApp.initDataUnsafe?.user && (
            <span>
              {WebApp.initDataUnsafe.user.first_name}{' '}
              {WebApp.initDataUnsafe.user.last_name || ''}
            </span>
          )}
        </div>
      </header>

      <div style={styles.content}>
        <AccountSwitcher
          key={accountsKey}
          selectedAccount={selectedAccount}
          onSelectAccount={handleSelectAccount}
          onDeleteAccount={handleAccountDeleted}
          onAddAccount={() => setShowAddAccount(true)}
        />

        {selectedAccount ? (
          <>
            <div style={styles.tabs}>
              <button
                style={{
                  ...styles.tab,
                  backgroundColor: activeTab === 'codes' ? '#1f538d' : 'transparent',
                }}
                onClick={() => setActiveTab('codes')}
              >
                🔑 Коды
              </button>
              <button
                style={{
                  ...styles.tab,
                  backgroundColor: activeTab === 'confirmations' ? '#1f538d' : 'transparent',
                }}
                onClick={() => setActiveTab('confirmations')}
              >
                ✅ Подтверждения
              </button>
              <button
                style={{
                  ...styles.tab,
                  backgroundColor: activeTab === 'trades' ? '#1f538d' : 'transparent',
                }}
                onClick={() => setActiveTab('trades')}
              >
                🤝 Трейды
              </button>
            </div>

            <div style={styles.tabContent}>
              {activeTab === 'codes' && (
                <CodeGenerator accountId={selectedAccount.id} />
              )}
              {activeTab === 'confirmations' && (
                <Confirmations accountId={selectedAccount.id} />
              )}
              {activeTab === 'trades' && <Trades accountId={selectedAccount.id} />}
            </div>
          </>
        ) : (
          <div style={styles.noAccount}>
            <p>Выберите аккаунт или добавьте новый</p>
            <p style={styles.hint}>Нажмите ➕ справа от кнопки выбора аккаунта</p>
          </div>
        )}
      </div>

      {showAddAccount && (
        <AddAccount
          onClose={() => setShowAddAccount(false)}
          onAccountAdded={handleAccountAdded}
        />
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  app: {
    minHeight: '100vh',
    backgroundColor: '#0e0e0e',
    color: '#ffffff',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    padding: '20px',
    backgroundColor: '#1a1a1a',
    borderBottom: '2px solid #1f538d',
    position: 'relative',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    textAlign: 'center',
  },
  userInfo: {
    textAlign: 'center',
    fontSize: '12px',
    color: '#888',
    marginTop: '5px',
  },
  content: {
    padding: '10px',
  },
  tabs: {
    display: 'flex',
    gap: '8px',
    marginBottom: '15px',
  },
  tab: {
    flex: 1,
    padding: '12px',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 'bold',
    transition: 'background-color 0.2s',
  },
  tabContent: {
    minHeight: '200px',
  },
  noAccount: {
    textAlign: 'center',
    padding: '40px 20px',
    color: '#888',
  },
  hint: {
    fontSize: '12px',
    marginTop: '10px',
  },
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
    padding: '30px',
    borderRadius: '12px',
    maxWidth: '90%',
    textAlign: 'center',
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
  },
};

export default App;
