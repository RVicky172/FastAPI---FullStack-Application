import { useAuth } from "./context/AuthContext.jsx";
import AuthForm from "./components/AuthForm.jsx";
import TodoList from "./components/TodoList.jsx";

export default function App() {
  const { user, loading, logout } = useAuth();

  if (loading) return <div className="center">Loading...</div>;

  return (
    <div className="container">
      <header className="header">
        <h1>📝 Todo App</h1>
        {user && (
          <div className="user">
            <span>Hi, <b>{user.username}</b></span>
            <button className="btn secondary" onClick={logout}>Logout</button>
          </div>
        )}
      </header>

      {user ? <TodoList /> : <AuthForm />}
    </div>
  );
}
