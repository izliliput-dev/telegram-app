/**
 * Утилиты для генерации 2FA кодов Steam Guard
 * Адаптированная версия из Python для JavaScript
 */

const SYMBOLS = '23456789BCDFGHJKMNPQRTVWXY';

let timeOffset = 0;

/**
 * Обновляет смещение времени относительно сервера Steam
 */
export async function updateTimeOffset(): Promise<number> {
  try {
    const response = await fetch('https://api.steampowered.com/ITwoFactorService/QueryTime/v0001', {
      method: 'POST',
    });
    const data = await response.json();
    const serverTime = parseInt(data.response.server_time);
    const localTime = Math.floor(Date.now() / 1000);
    timeOffset = serverTime - localTime;
    return timeOffset;
  } catch (error) {
    console.error('Ошибка синхронизации времени:', error);
    timeOffset = 0;
    return 0;
  }
}

/**
 * Генерирует код Steam Guard
 * @param sharedSecret - Базовый секрет из maFile (base64)
 */
export function getGuardCode(sharedSecret: string): string {
  if (!sharedSecret) {
    return '-----';
  }

  try {
    // Декодируем base64 секрет
    const secretBytes = base64ToBytes(sharedSecret);
    
    // Получаем текущее время с учётом смещения
    const currentTime = Math.floor((Date.now() / 1000 + timeOffset) / 30);
    
    // Создаём HMAC-SHA1 (синхронная версия для совместимости)
    const hmacArray = hmacSha1Sync(secretBytes, intToBytes(currentTime));
    
    // Получаем offset
    const offset = hmacArray[19] & 0xF;
    
    // Получаем 4 байта начиная с offset
    let fullCode = 0;
    for (let i = 0; i < 4; i++) {
      fullCode = (fullCode << 8) | hmacArray[offset + i];
    }
    fullCode = fullCode & 0x7fffffff;
    
    // Генерируем 5-символьный код
    let code = '';
    for (let i = 0; i < 5; i++) {
      code += SYMBOLS[fullCode % SYMBOLS.length];
      fullCode = Math.floor(fullCode / SYMBOLS.length);
    }
    
    return code;
  } catch (error) {
    console.error('Ошибка генерации кода:', error);
    return 'ERROR';
  }
}

/**
 * Возвращает количество секунд до смены кода
 */
export function getTimeRemaining(): number {
  const currentTime = Math.floor(Date.now() / 1000 + timeOffset);
  return 30 - (currentTime % 30);
}

/**
 * Конвертирует base64 строку в Uint8Array
 */
function base64ToBytes(base64: string): Uint8Array {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

/**
 * Конвертирует число в байты (big-endian)
 */
function intToBytes(value: number): Uint8Array {
  const bytes = new Uint8Array(8);
  for (let i = 7; i >= 0; i--) {
    bytes[i] = value & 0xff;
    value = Math.floor(value / 256);
  }
  return bytes;
}

/**
 * Вычисляет HMAC-SHA1 синхронно (для совместимости)
 * Использует упрощённую реализацию для работы в браузере
 */
function hmacSha1Sync(key: Uint8Array, data: Uint8Array): Uint8Array {
  // Упрощённая реализация HMAC-SHA1
  // Для продакшена лучше использовать Web Crypto API через async/await
  const blockSize = 64;
  const oKeyPad = new Uint8Array(blockSize);
  const iKeyPad = new Uint8Array(blockSize);
  
  // Если ключ больше blockSize, хешируем его (SHA1 = 20 байт)
  let actualKey = key;
  if (key.length > blockSize) {
    actualKey = sha1Sync(key);
  }
  
  // Заполняем падды
  for (let i = 0; i < blockSize; i++) {
    oKeyPad[i] = 0x5c ^ (i < actualKey.length ? actualKey[i] : 0);
    iKeyPad[i] = 0x36 ^ (i < actualKey.length ? actualKey[i] : 0);
  }
  
  // HMAC = H(oKeyPad || H(iKeyPad || message))
  const innerHash = sha1Sync(concatUint8Arrays(iKeyPad, data));
  const outerHash = sha1Sync(concatUint8Arrays(oKeyPad, innerHash));
  
  return outerHash;
}

/**
 * Синхронная реализация SHA1 (упрощённая)
 */
function sha1Sync(data: Uint8Array): Uint8Array {
  // Используем crypto.subtle через sync подход с Atomics
  // Для простоты используем внешний алгоритм
  const hash = simpleSha1(data);
  const result = new Uint8Array(20);
  for (let i = 0; i < 20; i++) {
    result[i] = hash[i] & 0xff;
  }
  return result;
}

/**
 * Простая реализация SHA1 для синхронной работы
 */
function simpleSha1(data: Uint8Array): number[] {
  // Инициализация хеш-значений
  let h0 = 0x67452301;
  let h1 = 0xefcdab89;
  let h2 = 0x98badcfe;
  let h3 = 0x10325476;
  let h4 = 0xc3d2e1f0;
  
  // Предварительная обработка
  const ml = data.length * 8;
  const newLength = ((ml + 65) >> 6) + 1 << 6;
  const bytes = new Uint8Array(newLength);
  bytes.set(data);
  bytes[data.length] = 0x80;

  // Добавляем длину в конце (big-endian)
  let mlTemp = ml;
  for (let i = 0; i < 8; i++) {
    bytes[newLength - 1 - i] = mlTemp & 0xff;
    mlTemp >>>= 8;
  }
  
  // Основная обработка
  for (let i = 0; i < newLength; i += 64) {
    const w = new Array(80);
    
    for (let j = 0; j < 16; j++) {
      w[j] = (bytes[i + j * 4] << 24) |
             (bytes[i + j * 4 + 1] << 16) |
             (bytes[i + j * 4 + 2] << 8) |
             bytes[i + j * 4 + 3];
    }
    
    for (let j = 16; j < 80; j++) {
      w[j] = leftRotate(w[j - 3] ^ w[j - 8] ^ w[j - 14] ^ w[j - 16], 1);
    }
    
    let a = h0, b = h1, c = h2, d = h3, e = h4;
    
    for (let j = 0; j < 80; j++) {
      let f: number, k: number;
      
      if (j < 20) {
        f = (b & c) | ((~b) & d);
        k = 0x5a827999;
      } else if (j < 40) {
        f = b ^ c ^ d;
        k = 0x6ed9eba1;
      } else if (j < 60) {
        f = (b & c) | (b & d) | (c & d);
        k = 0x8f1bbcdc;
      } else {
        f = b ^ c ^ d;
        k = 0xca62c1d6;
      }
      
      const temp = leftRotate(a, 5) + f + e + k + w[j] | 0;
      e = d;
      d = c;
      c = leftRotate(b, 30);
      b = a;
      a = temp;
    }
    
    h0 = h0 + a | 0;
    h1 = h1 + b | 0;
    h2 = h2 + c | 0;
    h3 = h3 + d | 0;
    h4 = h4 + e | 0;
  }
  
  return [h0, h1, h2, h3, h4];
}

function leftRotate(value: number, shift: number): number {
  return (value << shift) | (value >>> (32 - shift));
}

function concatUint8Arrays(a: Uint8Array, b: Uint8Array): Uint8Array {
  const result = new Uint8Array(a.length + b.length);
  result.set(a, 0);
  result.set(b, a.length);
  return result;
}
