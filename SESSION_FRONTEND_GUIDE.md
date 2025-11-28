# Gerenciamento de Sessão - React Frontend

## 📋 Implementação do Cliente

Este guia mostra como implementar o gerenciamento de sessão no React para trabalhar com o backend Flask.

## 🔧 Configuração Inicial

### 1. Axios com Cookies

```bash
npm install axios
```

```javascript
// src/api/axios.js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  withCredentials: true, // IMPORTANTE: Envia cookies automaticamente
  headers: {
    'Content-Type': 'application/json'
  }
});

// Interceptor para adicionar token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor para tratar expiração de sessão
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && error.response?.data?.session_expired) {
      // Sessão expirada
      handleSessionExpired(error.response.data.reason);
    }
    return Promise.reject(error);
  }
);

function handleSessionExpired(reason) {
  // Limpar dados locais
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  
  // Exibir mensagem apropriada
  const messages = {
    inactivity: 'Sua sessão expirou por inatividade. Faça login novamente.',
    max_lifetime: 'Sua sessão atingiu o tempo máximo. Faça login novamente.'
  };
  
  alert(messages[reason] || 'Sessão expirada. Faça login novamente.');
  
  // Redirecionar para login
  window.location.href = '/login';
}

export default api;
```

## 🔐 Hook de Autenticação

### 2. useAuth Hook

```javascript
// src/hooks/useAuth.js
import { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/axios';

const AuthContext = createContext({});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [sessionInfo, setSessionInfo] = useState(null);

  // Verificar sessão ao carregar
  useEffect(() => {
    checkSession();
  }, []);

  // Monitorar sessão periodicamente (a cada 5 minutos)
  useEffect(() => {
    const interval = setInterval(() => {
      checkSession();
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  // Renovar sessão automaticamente (a cada 10 minutos)
  useEffect(() => {
    if (!token) return;

    const interval = setInterval(() => {
      refreshSession();
    }, 10 * 60 * 1000);

    return () => clearInterval(interval);
  }, [token]);

  const checkSession = async () => {
    try {
      const response = await api.get('/session/status');
      
      if (response.data.active) {
        setSessionInfo(response.data);
        
        // Avisar se sessão próxima de expirar (< 5 min)
        if (response.data.inactivity_remaining_seconds < 300) {
          console.warn('⚠️ Sessão expirará em breve');
          // Você pode mostrar um toast ou modal aqui
        }
      } else {
        // Sem sessão ativa
        handleLogout();
      }
    } catch (error) {
      console.error('Erro ao verificar sessão:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshSession = async () => {
    try {
      await api.post('/session/refresh');
      console.log('✅ Sessão renovada automaticamente');
    } catch (error) {
      console.error('Erro ao renovar sessão:', error);
    }
  };

  const login = async (username, password) => {
    try {
      const response = await api.post('/login', {
        username,
        password
      });

      if (response.data.requires_mfa) {
        // Retornar para fluxo MFA
        return {
          requiresMFA: true,
          tempToken: response.data.temp_token
        };
      }

      // Login sem MFA
      const { token, user, session_info } = response.data;
      
      setToken(token);
      setUser(user);
      setSessionInfo(session_info);
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));

      return { requiresMFA: false, user };
    } catch (error) {
      throw error;
    }
  };

  const loginMFA = async (tempToken, totpCode) => {
    try {
      const response = await api.post('/login/mfa', {
        temp_token: tempToken,
        totp_code: totpCode
      });

      const { token, user, session_info } = response.data;
      
      setToken(token);
      setUser(user);
      setSessionInfo(session_info);
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));

      return { user };
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      await api.post('/logout');
    } catch (error) {
      console.error('Erro ao fazer logout:', error);
    } finally {
      handleLogout();
    }
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    setSessionInfo(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      sessionInfo,
      login,
      loginMFA,
      logout,
      checkSession,
      refreshSession
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

## 🖥️ Componentes de Login

### 3. Componente de Login

```javascript
// src/components/Login.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

function Login() {
  const navigate = useNavigate();
  const { login, loginMFA } = useAuth();
  
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  
  const [mfaStep, setMfaStep] = useState(false);
  const [tempToken, setTempToken] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login(formData.username, formData.password);

      if (result.requiresMFA) {
        // Ir para etapa MFA
        setMfaStep(true);
        setTempToken(result.tempToken);
      } else {
        // Login completo
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Erro ao fazer login');
    } finally {
      setLoading(false);
    }
  };

  const handleMFASubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await loginMFA(tempToken, totpCode);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || 'Código MFA inválido');
    } finally {
      setLoading(false);
    }
  };

  if (mfaStep) {
    return (
      <div className="login-container">
        <h2>Autenticação de Dois Fatores</h2>
        <form onSubmit={handleMFASubmit}>
          <input
            type="text"
            placeholder="Código TOTP (6 dígitos)"
            value={totpCode}
            onChange={(e) => setTotpCode(e.target.value)}
            maxLength={6}
            required
          />
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? 'Verificando...' : 'Verificar'}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="login-container">
      <h2>Login</h2>
      <form onSubmit={handleLogin}>
        <input
          type="text"
          placeholder="Username ou Email"
          value={formData.username}
          onChange={(e) => setFormData({ ...formData, username: e.target.value })}
          required
        />
        <input
          type="password"
          placeholder="Senha"
          value={formData.password}
          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          required
        />
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}

export default Login;
```

## 📊 Componente de Status da Sessão

### 4. Session Status Display

```javascript
// src/components/SessionStatus.jsx
import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';

function SessionStatus() {
  const { sessionInfo, checkSession } = useAuth();
  const [timeRemaining, setTimeRemaining] = useState('');

  useEffect(() => {
    // Atualizar display a cada segundo
    const interval = setInterval(() => {
      if (sessionInfo) {
        updateTimeDisplay();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [sessionInfo]);

  const updateTimeDisplay = () => {
    if (!sessionInfo) return;

    const inactivitySeconds = sessionInfo.inactivity_remaining_seconds;
    const lifetimeSeconds = sessionInfo.lifetime_remaining_seconds;
    
    const relevantSeconds = Math.min(inactivitySeconds, lifetimeSeconds);
    const minutes = Math.floor(relevantSeconds / 60);
    const seconds = relevantSeconds % 60;

    setTimeRemaining(`${minutes}:${seconds.toString().padStart(2, '0')}`);
  };

  if (!sessionInfo?.active) return null;

  const isNearExpiry = sessionInfo.inactivity_remaining_seconds < 300 || 
                       sessionInfo.lifetime_remaining_seconds < 300;

  return (
    <div className={`session-status ${isNearExpiry ? 'warning' : ''}`}>
      <span>⏱️ Sessão expira em: {timeRemaining}</span>
      {isNearExpiry && (
        <button onClick={checkSession}>Renovar Sessão</button>
      )}
    </div>
  );
}

export default SessionStatus;
```

## 🛡️ Proteção de Rotas

### 5. Protected Route Component

```javascript
// src/components/ProtectedRoute.jsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

function ProtectedRoute({ children }) {
  const { user, loading, sessionInfo } = useAuth();

  if (loading) {
    return <div>Carregando...</div>;
  }

  if (!user || !sessionInfo?.active) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default ProtectedRoute;
```

### 6. Uso no React Router

```javascript
// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './components/Login';
import Dashboard from './components/Dashboard';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          
          {/* Outras rotas protegidas */}
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
```

## 🔔 Notificações de Expiração

### 7. Session Expiry Warning

```javascript
// src/components/SessionExpiryWarning.jsx
import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';

function SessionExpiryWarning() {
  const { sessionInfo, refreshSession } = useAuth();
  const [showWarning, setShowWarning] = useState(false);

  useEffect(() => {
    if (!sessionInfo) return;

    const inactivityRemaining = sessionInfo.inactivity_remaining_seconds;
    const lifetimeRemaining = sessionInfo.lifetime_remaining_seconds;
    
    // Mostrar aviso se faltar menos de 3 minutos
    const shouldWarn = inactivityRemaining < 180 || lifetimeRemaining < 180;
    setShowWarning(shouldWarn);
  }, [sessionInfo]);

  if (!showWarning) return null;

  const handleExtend = async () => {
    await refreshSession();
    setShowWarning(false);
  };

  return (
    <div className="session-warning-modal">
      <div className="modal-content">
        <h3>⚠️ Sua sessão está prestes a expirar</h3>
        <p>
          {sessionInfo.will_expire_by === 'inactivity' 
            ? 'Sua sessão expirará por inatividade em breve.'
            : 'Sua sessão atingirá o tempo máximo em breve.'}
        </p>
        <div className="modal-actions">
          <button onClick={handleExtend} className="btn-primary">
            Continuar Conectado
          </button>
          <button onClick={() => window.location.href = '/login'} className="btn-secondary">
            Fazer Logout
          </button>
        </div>
      </div>
    </div>
  );
}

export default SessionExpiryWarning;
```

## 📱 Activity Tracker

### 8. User Activity Monitor

```javascript
// src/utils/activityMonitor.js
class ActivityMonitor {
  constructor(onActivity) {
    this.onActivity = onActivity;
    this.events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    this.throttleTime = 30000; // 30 segundos
    this.lastActivity = Date.now();
  }

  start() {
    this.events.forEach(event => {
      window.addEventListener(event, this.handleActivity.bind(this));
    });
  }

  stop() {
    this.events.forEach(event => {
      window.removeEventListener(event, this.handleActivity.bind(this));
    });
  }

  handleActivity() {
    const now = Date.now();
    
    // Throttle: só notifica se passou tempo suficiente
    if (now - this.lastActivity > this.throttleTime) {
      this.lastActivity = now;
      this.onActivity();
    }
  }
}

export default ActivityMonitor;
```

### 9. Uso do Activity Monitor

```javascript
// src/hooks/useAuth.js (adicionar ao AuthProvider)
import ActivityMonitor from '../utils/activityMonitor';

// Dentro do AuthProvider
useEffect(() => {
  if (!token) return;

  const monitor = new ActivityMonitor(() => {
    // Renovar sessão quando detectar atividade
    refreshSession();
  });

  monitor.start();

  return () => monitor.stop();
}, [token]);
```

## 🎨 Estilos CSS

```css
/* src/styles/session.css */

.session-status {
  position: fixed;
  top: 10px;
  right: 10px;
  padding: 10px 20px;
  background: #4caf50;
  color: white;
  border-radius: 5px;
  font-size: 14px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}

.session-status.warning {
  background: #ff9800;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.session-warning-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-content {
  background: white;
  padding: 30px;
  border-radius: 10px;
  max-width: 400px;
  text-align: center;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn-primary {
  flex: 1;
  padding: 10px;
  background: #73276C;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.btn-secondary {
  flex: 1;
  padding: 10px;
  background: #ccc;
  color: #333;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}
```

## ✅ Checklist de Implementação

- ✅ Axios configurado com `withCredentials: true`
- ✅ Interceptor para adicionar token automaticamente
- ✅ Interceptor para tratar expiração de sessão
- ✅ Hook useAuth com verificação periódica
- ✅ Renovação automática de sessão
- ✅ Componente de login com suporte MFA
- ✅ Proteção de rotas privadas
- ✅ Display de tempo restante
- ✅ Aviso de expiração próxima
- ✅ Monitor de atividade do usuário
- ✅ Tratamento de erros de sessão

## 🚀 Próximos Passos

1. Implementar toast notifications (react-toastify)
2. Adicionar loading states
3. Implementar refresh token automático
4. Adicionar logs de auditoria
5. Implementar "Remember Me" (opcional)
