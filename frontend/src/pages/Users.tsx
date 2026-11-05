import { FormEvent, useEffect, useState } from "react";
import { KeyRound, Loader2, Shield, UserRound, UserRoundPlus, UserRoundX } from "lucide-react";
import { useToast } from "../components/Toast";
import { api, extractErrorMessage } from "../services/api";
import { AuthUser } from "../types";

export default function Users() {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "user">("user");
  const [busyUserId, setBusyUserId] = useState<string | null>(null);
  const { push } = useToast();

  async function refresh() {
    setLoading(true);
    try {
      const response = await api.get<AuthUser[]>("/api/auth/users");
      setUsers(response.data);
    } catch (error) {
      push("error", extractErrorMessage(error, "Could not load accounts."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    try {
      const response = await api.post<AuthUser>("/api/auth/users", { username, password, role });
      setUsers((current) => [...current, response.data]);
      setUsername("");
      setPassword("");
      push("success", `Account ${response.data.username} created.`);
    } catch (error) {
      push("error", extractErrorMessage(error, "Could not create account."));
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(user: AuthUser) {
    setBusyUserId(user.id);
    try {
      const isActive = !user.is_active;
      await api.patch(`/api/auth/users/${user.id}`, { is_active: isActive });
      setUsers((current) => current.map((item) => item.id === user.id ? { ...item, is_active: isActive } : item));
      push("success", isActive ? "Account enabled." : "Account disabled and sessions revoked.");
    } catch (error) {
      push("error", extractErrorMessage(error, "Could not update account."));
    } finally {
      setBusyUserId(null);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-5 py-7 sm:px-8 sm:py-9">
      <header className="mb-6">
        <p className="mb-2 text-xs font-medium text-accent">WORKSPACE / ACCESS</p>
        <h1 className="text-3xl font-semibold text-white">Users</h1>
        <p className="mt-2 text-sm text-zinc-400">Create accounts and manage access to this workspace.</p>
      </header>

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.85fr)]">
        <section className="card p-5">
          <div className="mb-4 flex items-center gap-2">
            <UserRoundPlus size={17} className="text-accent" />
            <h2 className="text-sm font-semibold text-white">Create account</h2>
          </div>
          <form onSubmit={handleCreate} className="space-y-4">
            <label className="block text-sm text-zinc-300">
              Username
              <input required minLength={3} maxLength={32} value={username} onChange={(event) => setUsername(event.target.value)} className="input mt-2" autoComplete="off" />
            </label>
            <label className="block text-sm text-zinc-300">
              Temporary password
              <input required minLength={10} maxLength={128} type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="input mt-2" autoComplete="new-password" />
              <span className="mt-1 block text-xs text-zinc-500">At least 10 characters. Share it privately with the user.</span>
            </label>
            <label className="block text-sm text-zinc-300">
              Role
              <select value={role} onChange={(event) => setRole(event.target.value as "admin" | "user")} className="input mt-2">
                <option value="user">User · run models and manage own history</option>
                <option value="admin">Admin · full access</option>
              </select>
            </label>
            <button type="submit" disabled={creating} className="btn-primary flex min-h-10 w-full items-center justify-center gap-2 px-4 py-2 text-sm font-medium disabled:opacity-50">
              {creating ? <Loader2 size={15} className="animate-spin" /> : <UserRoundPlus size={15} />}
              Create account
            </button>
          </form>
        </section>

        <section className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-white/[0.08] px-5 py-4">
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-emerald-200" />
              <h2 className="text-sm font-semibold text-white">Accounts</h2>
            </div>
            <span className="text-xs text-zinc-500">{users.length}</span>
          </div>
          {loading ? (
            <p className="px-5 py-6 text-sm text-zinc-400">Loading accounts...</p>
          ) : (
            <div className="divide-y divide-white/[0.06]">
              {users.map((user) => (
                <div key={user.id} className="flex items-center gap-3 px-5 py-4">
                  <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md border ${user.role === "admin" ? "border-accent/20 bg-accent/10 text-accent" : "border-white/10 bg-white/[0.03] text-zinc-300"}`}>
                    {user.role === "admin" ? <Shield size={16} /> : <UserRound size={16} />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-white">{user.username}</span>
                    <span className="mt-1 block text-xs capitalize text-zinc-500">{user.role} · {user.is_active ? "Active" : "Disabled"}</span>
                  </span>
                  <button
                    type="button"
                    aria-label={`${user.is_active ? "Disable" : "Enable"} ${user.username}`}
                    title={user.is_active ? "Disable account" : "Enable account"}
                    disabled={busyUserId === user.id}
                    onClick={() => void toggleActive(user)}
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 text-zinc-400 hover:border-slate-300/20 hover:text-slate-200 disabled:opacity-50"
                  >
                    {busyUserId === user.id ? <Loader2 size={15} className="animate-spin" /> : user.is_active ? <UserRoundX size={16} /> : <KeyRound size={16} />}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}