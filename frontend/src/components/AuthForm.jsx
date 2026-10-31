import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";

export default function AuthForm() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isLogin = mode === "login";

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (isLogin) await login(form.username, form.password);
      else await register(form.username, form.password);
    } catch (err) {
      setError(err.message); // already made readable by the interceptor
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="card auth" onSubmit={handleSubmit}>
      <h2>{isLogin ? "Login" : "Create account"}</h2>

      <input name="username" placeholder="Username" value={form.username}
             onChange={handleChange} autoComplete="username" required />
      <input name="password" type="password" placeholder="Password (min 6 chars)"
             value={form.password} onChange={handleChange}
             autoComplete={isLogin ? "current-password" : "new-password"} required />

      {error && <p className="error">{error}</p>}

      <button className="btn" disabled={submitting}>
        {submitting ? "Please wait..." : isLogin ? "Login" : "Register"}
      </button>

      <p className="muted">
        {isLogin ? "No account?" : "Already registered?"}{" "}
        <button type="button" className="link"
                onClick={() => { setMode(isLogin ? "register" : "login"); setError(""); }}>
          {isLogin ? "Register" : "Login"}
        </button>
      </p>
    </form>
  );
}
