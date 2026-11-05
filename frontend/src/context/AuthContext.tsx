import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { api } from "../services/api";
import { AuthUser } from "../types";

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  setupRequired: boolean;
  registrationEnabled: boolean;
  passwordRecoveryEnabled: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  registerUser: (username: string, password: string) => Promise<void>;
  setupAdmin: (username: string, password: string, setupKey: string) => Promise<void>;
  resetPassword: (username: string, recoveryKey: string, newPassword: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth must be used within AuthProvider");
  return auth;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [setupRequired, setSetupRequired] = useState(false);
  const [registrationEnabled, setRegistrationEnabled] = useState(false);
  const [passwordRecoveryEnabled, setPasswordRecoveryEnabled] = useState(false);

  useEffect(() => {
    api.get("/api/auth/status")
      .then((response) => {
        setUser(response.data.user);
        setSetupRequired(response.data.setup_required);
        setRegistrationEnabled(response.data.registration_enabled === true);
        setPasswordRecoveryEnabled(response.data.password_recovery_enabled === true);
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  async function signIn(username: string, password: string) {
    const response = await api.post<AuthUser>("/api/auth/login", { username, password });
    setUser(response.data);
    setSetupRequired(false);
  }

  async function registerUser(username: string, password: string) {
    const response = await api.post<AuthUser>("/api/auth/register", { username, password });
    setUser(response.data);
    setSetupRequired(false);
  }

  async function setupAdmin(username: string, password: string, setupKey: string) {
    const response = await api.post<AuthUser>(
      "/api/auth/setup",
      { username, password },
      { headers: { "X-Initial-Admin-Setup-Key": setupKey } },
    );
    setUser(response.data);
    setSetupRequired(false);
  }

  async function resetPassword(username: string, recoveryKey: string, newPassword: string) {
    await api.post("/api/auth/password-reset", {
      username,
      recovery_key: recoveryKey,
      new_password: newPassword,
    });
  }

  async function signOut() {
    setUser(null);
    setSetupRequired(false);
    try {
      await api.post("/api/auth/logout");
    } catch {
      // Keep the current page signed out if the server cannot be reached.
    }
  }

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      setupRequired,
      registrationEnabled,
      passwordRecoveryEnabled,
      signIn,
      registerUser,
      setupAdmin,
      resetPassword,
      signOut,
    }}>
      {children}
    </AuthContext.Provider>
  );
}