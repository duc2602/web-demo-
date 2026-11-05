import { FormEvent, useState } from "react";
import { ArrowRight, LogIn, ShieldCheck, UserPlus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage } from "../services/api";

export default function AuthPage({ initialSetup }: { initialSetup: boolean }) {
  const { signIn, registerUser, setupAdmin, resetPassword, registrationEnabled, passwordRecoveryEnabled } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [setupKey, setSetupKey] = useState("");
  const [recoveryKey, setRecoveryKey] = useState("");
  const [recoveryMode, setRecoveryMode] = useState(false);
  const [registerMode, setRegisterMode] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");
    if ((initialSetup || recoveryMode || registerMode) && password !== confirmation) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      if (initialSetup) await setupAdmin(username, password, setupKey);
      else if (recoveryMode) {
        await resetPassword(username, recoveryKey, password);
        setRecoveryMode(false);
        setRecoveryKey("");
        setPassword("");
        setConfirmation("");
        setNotice("Password reset. Sign in with your new password.");
      } else if (registerMode) await registerUser(username, password);
      else await signIn(username, password);
    } catch (requestError) {
      setError(extractErrorMessage(requestError, "Unable to authenticate. Check the details and try again."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center overflow-y-auto bg-bg px-5 py-10">
      <div className="w-full max-w-md">
        <div className="mb-7 flex items-center gap-3">
          <img src="/logo.svg" alt="" className="h-11 w-11" />
          <div>
            <p className="text-sm font-semibold text-white">Model Khôi Phục Chữ Viết</p>
            <p className="mt-0.5 text-xs text-zinc-400">Private image restoration workspace</p>
          </div>
        </div>

        <section className="card p-6 sm:p-7">
          <div className="mb-6 flex h-10 w-10 items-center justify-center rounded-md border border-accent/20 bg-accent/10">
            <ShieldCheck size={19} className="text-accent" />
          </div>
          <h1 className="text-xl font-semibold text-white">
            {initialSetup ? "Create administrator" : recoveryMode ? "Reset password" : registerMode ? "Create account" : "Sign in"}
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-zinc-400">
            {initialSetup
              ? "Set up the first administrator account. The workspace stays private until an account is created."
              : recoveryMode
                ? "Enter your username, server recovery key, and a new password."
                : registerMode
                  ? "Create a user account to access the workspace."
                  : "Sign in to your workspace account."}
          </p>

          {!initialSetup && !recoveryMode && registrationEnabled && (
            <div role="tablist" aria-label="Account access" className="mt-5 grid grid-cols-2 gap-1 rounded-lg border border-white/10 bg-black/20 p-1">
              <button
                type="button"
                role="tab"
                aria-selected={!registerMode}
                onClick={() => { setRegisterMode(false); setError(""); setNotice(""); }}
                className={`flex min-h-10 items-center justify-center gap-2 rounded-md px-3 text-sm transition-colors ${!registerMode ? "bg-white/10 text-white" : "text-zinc-400 hover:text-white"}`}
              >
                <LogIn size={15} /> Đăng nhập
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={registerMode}
                onClick={() => { setRegisterMode(true); setError(""); setNotice(""); }}
                className={`flex min-h-10 items-center justify-center gap-2 rounded-md px-3 text-sm transition-colors ${registerMode ? "bg-white/10 text-white" : "text-zinc-400 hover:text-white"}`}
              >
                <UserPlus size={15} /> Đăng ký
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block text-sm text-zinc-300">
              Username
              <input
                autoComplete="username"
                autoFocus
                required
                minLength={3}
                maxLength={32}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="input mt-2"
                placeholder="username"
              />
            </label>
            {initialSetup && (
              <label className="block text-sm text-zinc-300">
                Initial setup key
                <input
                  autoComplete="off"
                  required
                  minLength={32}
                  maxLength={256}
                  type="password"
                  value={setupKey}
                  onChange={(event) => setSetupKey(event.target.value)}
                  className="input mt-2"
                  placeholder="Server initial setup key"
                />
              </label>
            )}
            {recoveryMode && (
              <label className="block text-sm text-zinc-300">
                Recovery key
                <input
                  autoComplete="off"
                  required
                  minLength={32}
                  maxLength={256}
                  type="password"
                  value={recoveryKey}
                  onChange={(event) => setRecoveryKey(event.target.value)}
                  className="input mt-2"
                  placeholder="Server recovery key"
                />
              </label>
            )}
            <label className="block text-sm text-zinc-300">
              {recoveryMode ? "New password" : "Password"}
              <input
                autoComplete={initialSetup || recoveryMode || registerMode ? "new-password" : "current-password"}
                required
                minLength={initialSetup || recoveryMode || registerMode ? 10 : 1}
                maxLength={128}
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="input mt-2"
                placeholder={initialSetup ? "At least 10 characters" : "Password"}
              />
            </label>
            {(initialSetup || recoveryMode || registerMode) && (
              <label className="block text-sm text-zinc-300">
                Confirm password
                <input
                  autoComplete="new-password"
                  required
                  minLength={10}
                  maxLength={128}
                  type="password"
                  value={confirmation}
                  onChange={(event) => setConfirmation(event.target.value)}
                  className="input mt-2"
                  placeholder="Repeat password"
                />
              </label>
            )}
            {error && <p role="alert" className="rounded-lg border border-slate-300/15 bg-slate-400/[0.06] px-3 py-2.5 text-sm text-slate-200">{error}</p>}
            {notice && <p role="status" className="rounded-lg border border-emerald-300/15 bg-emerald-400/[0.06] px-3 py-2.5 text-sm text-emerald-200">{notice}</p>}
            <button type="submit" disabled={submitting} className="btn-primary flex min-h-11 w-full items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium disabled:opacity-50">
              {submitting ? "Please wait..." : initialSetup ? "Create admin account" : recoveryMode ? "Reset password" : registerMode ? "Create account" : "Sign in"}
              {!submitting && <ArrowRight size={16} />}
            </button>
          </form>
          {!initialSetup && !registerMode && passwordRecoveryEnabled && !recoveryMode && (
            <button
              type="button"
              onClick={() => { setRecoveryMode(true); setError(""); setNotice(""); }}
              className="mt-4 text-sm text-accent hover:text-white"
            >
              Forgot password?
            </button>
          )}
          {!initialSetup && !registerMode && !passwordRecoveryEnabled && (
            <p className="mt-4 text-xs leading-relaxed text-zinc-500">
              Password recovery is not configured. Ask the server administrator to set ACCOUNT_RECOVERY_KEY in backend/.env.
            </p>
          )}
          {recoveryMode && (
            <button
              type="button"
              onClick={() => { setRecoveryMode(false); setError(""); setNotice(""); }}
              className="mt-4 text-sm text-zinc-400 hover:text-white"
            >
              Back to sign in
            </button>
          )}
        </section>
        <p className="mt-5 text-center text-xs text-zinc-500">Accounts and sessions are stored on this server.</p>
      </div>
    </main>
  );
}