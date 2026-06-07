import React, { useState, useEffect } from 'react';
import { codeApi, accountsApi } from '../api/api';
import { getGuardCode, getTimeRemaining, updateTimeOffset } from '../utils/steamGuard';

interface CodeGeneratorProps {
  accountId: string;
}

export const CodeGenerator: React.FC<CodeGeneratorProps> = ({ accountId }) => {
  const [code, setCode] = useState<string>('-----');
  const [timeRemaining, setTimeRemaining] = useState<number>(30);
  const [loading, setLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [sharedSecret, setSharedSecret] = useState<string>('');

  // Загружаем shared_secret и identity_secret аккаунта
  useEffect(() => {
    const loadAccountData = async () => {
      try {
        const response = await accountsApi.getById(accountId);
        if (response.data.shared_secret) {
          setSharedSecret(response.data.shared_secret);
        }
      } catch (error) {
        console.error('Ошибка загрузки данных аккаунта:', error);
      }
    };
    
    if (accountId) {
      loadAccountData();
    }
  }, [accountId]);

  // Функция получения кода (с бэкенда или локально)
  const fetchCode = async () => {
    if (!accountId) return;

    setLoading(true);
    try {
      // Пробуем получить с бэкенда
      const response = await codeApi.getCode(accountId);
      const backendCode = response.data.code;
      
      // Если бэкенд вернул код, используем его
      if (backendCode && backendCode !== '-----' && backendCode !== 'ERROR') {
        setCode(backendCode);
        setTimeRemaining(response.data.time_remaining);
      } else if (sharedSecret) {
        // Если бэкенд не вернул, генерируем локально
        const localCode = getGuardCode(sharedSecret);
        setCode(localCode);
        setTimeRemaining(getTimeRemaining());
      } else {
        setCode('-----');
      }
    } catch (error) {
      console.error('Ошибка получения кода:', error);
      // Фоллбэк на локальную генерацию
      if (sharedSecret) {
        const localCode = getGuardCode(sharedSecret);
        setCode(localCode);
        setTimeRemaining(getTimeRemaining());
      } else {
        setCode('ERROR');
      }
    } finally {
      setLoading(false);
    }
  };

  // Копирование кода в буфер
  const copyToClipboard = () => {
    if (code && code !== '-----' && code !== 'ERROR') {
      navigator.clipboard.writeText(code);
      setCopied(true);
      
      // Вибрация через Telegram
      const tg = (window as any).Telegram.WebApp;
      if (tg && tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
      }
      
      // Сброс через 1 секунду
      setTimeout(() => setCopied(false), 1000);
    }
  };

  // Обновление кода
  useEffect(() => {
    if (!accountId) return;

    // Синхронизация времени при монтировании
    updateTimeOffset();

    // Первая загрузка кода
    fetchCode();

    // Таймер обновления
    const interval = setInterval(() => {
      const remaining = getTimeRemaining();
      setTimeRemaining(remaining);

      if (remaining <= 5 || remaining === 30) {
        fetchCode();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [accountId, sharedSecret]);

  // Прогресс бар
  const progress = ((30 - timeRemaining) / 30) * 100;

  return (
    <div style={styles.container}>
      <div style={styles.codeBlock}>
        <div style={styles.code} onClick={copyToClipboard}>
          {loading ? '...' : code}
        </div>
        <div style={styles.timer}>{timeRemaining}s</div>
      </div>
      
      <div style={styles.progressBar}>
        <div style={{ ...styles.progressFill, width: `${progress}%` }} />
      </div>
      
      <button
        style={{
          ...styles.copyButton,
          backgroundColor: copied ? '#28a745' : '#1f538d',
          transform: copied ? 'scale(1.05)' : 'scale(1)',
        }}
        onClick={copyToClipboard}
      >
        {copied ? '✅ Скопировано!' : '📋 Скопировать код'}
      </button>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    padding: '20px',
    backgroundColor: '#2b2b2b',
    borderRadius: '12px',
    margin: '10px',
  },
  codeBlock: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    marginBottom: '15px',
  },
  code: {
    fontSize: '48px',
    fontWeight: 'bold',
    color: '#1f538d',
    cursor: 'pointer',
    fontFamily: 'monospace',
    letterSpacing: '8px',
  },
  timer: {
    fontSize: '14px',
    color: '#888',
    marginTop: '5px',
  },
  progressBar: {
    width: '100%',
    height: '8px',
    backgroundColor: '#1a1a1a',
    borderRadius: '4px',
    overflow: 'hidden',
    marginBottom: '15px',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#1f538d',
    transition: 'width 0.3s ease',
  },
  copyButton: {
    width: '100%',
    padding: '12px',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 'bold',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
};

export default CodeGenerator;
