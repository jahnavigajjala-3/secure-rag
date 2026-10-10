/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { authApi } from '../../api/auth';
import { ApiError } from '../../api/client';
import type { AuthState, User } from '../../types/auth';

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<User>;
  register: (payload: {
    name: string;
    email: string;
    password: string;
    confirm_password: string;
    account_type?: 'employee' | 'admin';
    admin_access_key?: string;
  }) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<User | null>;
  isLoading: boolean;
}

const defaultAuthState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>(() => {
    const token = localStorage.getItem('secure_rag_token');
    const storedUser = localStorage.getItem('secure_rag_user');

    if (!token || !storedUser) {
      return defaultAuthState;
    }

    try {
      const user = JSON.parse(storedUser) as User;
      return {
        user,
        token,
        isAuthenticated: true,
      };
    } catch {
      return defaultAuthState;
    }
  });
  const [isLoading, setIsLoading] = useState(true);

  const storeToken = useCallback((token: string | null) => {
    if (token) {
      localStorage.setItem('secure_rag_token', token);
    } else {
      localStorage.removeItem('secure_rag_token');
    }
  }, []);

  const clearAuth = useCallback(() => {
    // eslint-disable-next-line no-console
    console.debug('[auth] clearAuth called — clearing local state and storage');
    setAuthState({ user: null, token: null, isAuthenticated: false });
    localStorage.removeItem('secure_rag_token');
    localStorage.removeItem('secure_rag_user');
  }, []);

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('secure_rag_token');
    if (!token) {
      clearAuth();
      setIsLoading(false);
      return null;
    }

    try {
      const user = await authApi.me();
      const nextState = { user, token, isAuthenticated: true };
      setAuthState(nextState);
      localStorage.setItem('secure_rag_user', JSON.stringify(user));
      setIsLoading(false);
      return user;
    } catch (error) {
      const apiError = error as ApiError;
      if (apiError.status === 401 || apiError.status === 403) {
        clearAuth();
      }
      setIsLoading(false);
      return null;
    }
  }, [clearAuth]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login({ email, password });
    const nextUser = response.user;
    storeToken(response.access_token);
    // eslint-disable-next-line no-console
    console.debug('[auth] login success', { user: nextUser, hasToken: Boolean(response.access_token) });
    setAuthState({
      user: nextUser,
      token: response.access_token,
      isAuthenticated: true,
    });
    localStorage.setItem('secure_rag_user', JSON.stringify(nextUser));
    return nextUser;
  }, [storeToken]);

  const register = useCallback(async (payload: {
    name: string;
    email: string;
    password: string;
    confirm_password: string;
    account_type?: 'employee' | 'admin';
    admin_access_key?: string;
  }) => {
    const response = await authApi.register(payload);
    return response.user;
  }, []);

  const logout = useCallback(() => {
    clearAuth();
  }, [clearAuth]);

  useEffect(() => {
    let ignore = false;

    const bootstrap = async () => {
      const token = localStorage.getItem('secure_rag_token');
      // eslint-disable-next-line no-console
      console.debug('[auth] bootstrap — token in storage?', Boolean(token));
      if (!token) {
        setAuthState(defaultAuthState);
        setIsLoading(false);
        return;
      }

      try {
        const user = await authApi.me();
        if (!ignore) {
          setAuthState({ user, token, isAuthenticated: true });
          localStorage.setItem('secure_rag_user', JSON.stringify(user));
          setIsLoading(false);
        }
      } catch (error) {
        const apiError = error as ApiError;
        // eslint-disable-next-line no-console
        console.warn('[auth] bootstrap failed', { error: apiError?.message ?? error, status: apiError?.status });
        if (!ignore) {
          if (apiError.status === 401 || apiError.status === 403) {
            setAuthState(defaultAuthState);
            localStorage.removeItem('secure_rag_token');
            localStorage.removeItem('secure_rag_user');
          }
          setIsLoading(false);
        }
      }
    };

    void bootstrap();

    return () => {
      ignore = true;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...authState,
      login,
      register,
      logout,
      refreshUser,
      isLoading,
    }),
    [authState, isLoading, login, logout, refreshUser, register],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
