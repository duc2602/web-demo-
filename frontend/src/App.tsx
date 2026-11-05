import { Navigate, Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import { ToastProvider } from "./components/Toast";
import { AppProvider } from "./context/AppContext";   
import { AuthProvider, useAuth } from "./context/AuthContext";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import Models from "./pages/Models";
import History from "./pages/History";
import Trash from "./pages/Trash";
import Settings from "./pages/Settings";
import Users from "./pages/Users";

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <AuthenticatedApp />
      </AuthProvider>
    </ToastProvider>
  );
}

function AuthenticatedApp() {
  const { user, loading, setupRequired, signOut } = useAuth();

  if (loading) {
    return <div className="flex h-screen items-center justify-center bg-bg text-sm text-zinc-400">Checking access...</div>;
  }

  if (setupRequired || !user) {
    return <AuthPage initialSetup={setupRequired} />;
  }

  return (
    <AppProvider>
        <div className="app-shell flex h-screen flex-col overflow-hidden bg-bg md:flex-row">
          <Sidebar user={user} onSignOut={signOut} />
          <main className="app-main min-w-0 flex-1 overflow-y-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/models" element={<Models />} />
              <Route path="/history" element={<History />} />
              <Route path="/trash" element={<Trash />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/users" element={user.role === "admin" ? <Users /> : <Navigate to="/" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
    </AppProvider>
  );
}
