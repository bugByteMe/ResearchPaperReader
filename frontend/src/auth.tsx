import { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import { api, CurrentUser } from './api/client';

type AuthContextValue = {
  user: CurrentUser;
  loading: boolean;
  isAdmin: boolean;
  login: (password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const defaultUser: CurrentUser = { role: 'reader' };
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser>(defaultUser);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCurrentUser()
      .then(setUser)
      .catch(() => setUser(defaultUser))
      .finally(() => setLoading(false));
  }, []);

  const login = async (password: string) => {
    setUser(await api.login(password));
  };

  const logout = async () => {
    setUser(await api.logout());
  };

  return (
    <AuthContext.Provider value={{ user, loading, isAdmin: user.role === 'admin', login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
