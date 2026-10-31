/**
 * Global auth state: who is logged in, plus login/register/logout actions.
 * Any component can read it with `useAuth()`.
 */
import { createContext, use, useCallback, useEffect, useState } from "react";
import { tokenStorage } from "../api/axiosClient";
import { authApi } from "../api/services";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true while checking a saved token

  // Forget the token locally (used when the server already rejected it)
  const clearSession = useCallback(() => {
    tokenStorage.clear();
    setUser(null);
  }, []);

  // Real logout: ask the server to revoke the token in the DB, so it can't be
  // reused even if someone copied it. Clear locally whatever happens.
  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // token already invalid / server down - nothing more to revoke
    }
    clearSession();
  }, [clearSession]);

  // On first load: if a token is saved, ask the backend who we are.
  useEffect(() => {
    if (!tokenStorage.get()) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(clearSession) // token expired/revoked -> interceptor already cleared it
      .finally(() => setLoading(false));
  }, [clearSession]);

  // The axios response interceptor fires this event on any 401.
  useEffect(() => {
    window.addEventListener("auth:logout", clearSession);
    return () => window.removeEventListener("auth:logout", clearSession);
  }, [clearSession]);

  const login = async (username, password) => {
    const { access_token } = await authApi.login(username, password);
    tokenStorage.set(access_token);
    setUser(await authApi.me()); // interceptor now attaches the new token
  };

  const register = async (username, password) => {
    await authApi.register(username, password);
    await login(username, password);
  };

  return (
    // React 19: <Context> can be used directly as the provider
    <AuthContext value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext>
  );
}

export function useAuth() {
  // React 19: `use()` reads context (works like useContext)
  return use(AuthContext);
}
