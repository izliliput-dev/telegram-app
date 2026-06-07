import React, { useState } from 'react';
import api from '../api/api';

interface AddAccountProps {
  onClose: () => void;
  onAccountAdded: () => void;
}

export const AddAccount: React.FC<AddAccountProps> = ({ onClose, onAccountAdded }) => {
  const [step, setStep] = useState<'file' | 'credentials' | 'loading'>('file');
  const [mafileName, setMafileName] = useState('');
  const [mafileData, setMafileData] = useState<any>(null);
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        setMafileData(data);
        setMafileName(file.name.replace('.maFile', ''));
        setStep('credentials');
        setError('');
      } catch (err) {
        setError('Неверный формат файла .maFile');
      }
    };
    reader.readAsText(file);
  };

  const handleSubmit = async () => {
    if (!login || !password) {
      setError('Введите логин и пароль');
      return;
    }

    setStep('loading');
    setError('');

    try {
      await api.post('/api/accounts', {
        name: mafileName || login,
        mafile_data: mafileData,
        steam_login: login,
        steam_password: password,
      });
      onAccountAdded();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка при добавлении аккаунта');
      setStep('credentials');
    }
  };

  return (
    <div style={styles.modal}>
      <div style={styles.modalContent}>
        <h2 style={styles.title}>➕ Добавление аккаунта</h2>

        {error && <div style={styles.error}>{error}</div>}

        {step === 'file' && (
          <>
            <p style={styles.description}>
              Выберите файл .maFile из папки maFiles Steam Desktop Authenticator
            </p>
            <label style={styles.fileLabel}>
              <input
                type="file"
                accept=".maFile"
                onChange={handleFileSelect}
                style={styles.fileInput}
              />
              <span style={styles.fileButton}>📁 Выбрать файл</span>
            </label>
          </>
        )}

        {step === 'credentials' && (
          <>
            <p style={styles.description}>
              Введите данные от Steam аккаунта для обновления сессии
            </p>
            <input
              type="text"
              placeholder="Логин Steam"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              style={styles.input}
            />
            <input
              type="password"
              placeholder="Пароль Steam"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
            />
            <div style={styles.buttons}>
              <button style={styles.backButton} onClick={() => setStep('file')}>
                ← Назад
              </button>
              <button style={styles.submitButton} onClick={handleSubmit}>
                ✅ Добавить аккаунт
              </button>
            </div>
          </>
        )}

        {step === 'loading' && (
          <div style={styles.loading}>
            <div style={styles.spinner}></div>
            <p>Проверка данных и обновление сессии...</p>
          </div>
        )}

        <button style={styles.closeButton} onClick={onClose}>
          ✕ Закрыть
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
    padding: '30px',
    borderRadius: '12px',
    maxWidth: '90%',
    width: '400px',
    textAlign: 'center',
  },
  title: {
    margin: '0 0 20px 0',
    fontSize: '20px',
    color: '#ffffff',
  },
  description: {
    color: '#888',
    fontSize: '14px',
    marginBottom: '20px',
    lineHeight: '1.5',
  },
  fileLabel: {
    display: 'block',
    cursor: 'pointer',
    padding: '20px',
    border: '2px dashed #1f538d',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  fileInput: {
    display: 'none',
  },
  fileButton: {
    display: 'inline-block',
    padding: '12px 24px',
    backgroundColor: '#1f538d',
    color: 'white',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 'bold',
  },
  input: {
    width: '100%',
    padding: '12px',
    marginBottom: '15px',
    backgroundColor: '#2b2b2b',
    border: '1px solid #333',
    borderRadius: '8px',
    color: 'white',
    fontSize: '14px',
    boxSizing: 'border-box',
  },
  buttons: {
    display: 'flex',
    gap: '10px',
    marginBottom: '20px',
  },
  backButton: {
    flex: 1,
    padding: '12px',
    backgroundColor: 'transparent',
    color: 'white',
    border: '1px solid #333',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  submitButton: {
    flex: 1,
    padding: '12px',
    backgroundColor: '#28a745',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
  },
  loading: {
    padding: '20px',
  },
  spinner: {
    border: '3px solid #333',
    borderTop: '3px solid #1f538d',
    borderRadius: '50%',
    width: '40px',
    height: '40px',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 15px',
  },
  error: {
    backgroundColor: '#dc3545',
    color: 'white',
    padding: '10px',
    borderRadius: '8px',
    marginBottom: '15px',
    fontSize: '13px',
  },
  closeButton: {
    padding: '10px 20px',
    backgroundColor: 'transparent',
    color: '#888',
    border: '1px solid #333',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
  },
};

export default AddAccount;
