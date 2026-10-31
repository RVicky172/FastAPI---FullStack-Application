import { useEffect, useState } from "react";
import { todoApi } from "../api/services";

const FILTERS = { all: undefined, active: false, done: true };

export default function TodoList() {
  const [todos, setTodos] = useState([]);
  const [title, setTitle] = useState("");
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // Re-fetch whenever the filter changes (filtering happens on the backend
  // via the ?completed= query param).
  useEffect(() => {
    setLoading(true);
    todoApi
      .list(FILTERS[filter])
      .then(setTodos)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filter]);

  const run = async (fn) => {
    setError("");
    try {
      await fn();
    } catch (err) {
      setError(err.message);
    }
  };

  const addTodo = (e) => {
    e.preventDefault();
    run(async () => {
      const todo = await todoApi.create(title);
      if (filter !== "done") setTodos((prev) => [todo, ...prev]);
      setTitle("");
    });
  };

  const toggleTodo = (todo) =>
    run(async () => {
      const updated = await todoApi.update(todo.id, { completed: !todo.completed });
      setTodos((prev) =>
        filter === "all"
          ? prev.map((t) => (t.id === updated.id ? updated : t))
          : prev.filter((t) => t.id !== updated.id) // no longer matches filter
      );
    });

  const editTodo = (todo) => {
    const newTitle = prompt("Edit todo", todo.title);
    if (!newTitle || newTitle === todo.title) return;
    run(async () => {
      const updated = await todoApi.update(todo.id, { title: newTitle });
      setTodos((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    });
  };

  const deleteTodo = (id) =>
    run(async () => {
      await todoApi.remove(id);
      setTodos((prev) => prev.filter((t) => t.id !== id));
    });

  return (
    <div className="card">
      <form className="row" onSubmit={addTodo}>
        <input value={title} onChange={(e) => setTitle(e.target.value)}
               placeholder="What needs to be done?" />
        <button className="btn" disabled={!title.trim()}>Add</button>
      </form>

      <div className="filters">
        {Object.keys(FILTERS).map((f) => (
          <button key={f} className={`chip ${filter === f ? "active" : ""}`}
                  onClick={() => setFilter(f)}>
            {f}
          </button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Loading...</p>
      ) : todos.length === 0 ? (
        <p className="muted">Nothing here yet.</p>
      ) : (
        <ul className="todos">
          {todos.map((todo) => (
            <li key={todo.id} className={todo.completed ? "done" : ""}>
              <input type="checkbox" checked={todo.completed}
                     onChange={() => toggleTodo(todo)} />
              <span className="title" onDoubleClick={() => editTodo(todo)}
                    title="Double-click to edit">
                {todo.title}
              </span>
              <button className="icon" onClick={() => editTodo(todo)} aria-label="Edit">✏️</button>
              <button className="icon" onClick={() => deleteTodo(todo.id)} aria-label="Delete">🗑️</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
