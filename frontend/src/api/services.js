// Thin functions around the API so components never deal with URLs.
import api from "./axiosClient";

export const authApi = {
  register: (username, password) =>
    api.post("/auth/register", { username, password }).then((r) => r.data),
  login: (username, password) =>
    api.post("/auth/login", { username, password }).then((r) => r.data),
  me: () => api.get("/auth/me").then((r) => r.data),
  logout: () => api.post("/auth/logout"), // server marks the token revoked
};

export const todoApi = {
  list: (completed) =>
    api.get("/todos", { params: { completed } }).then((r) => r.data),
  create: (title, description) =>
    api.post("/todos", { title, description }).then((r) => r.data),
  update: (id, changes) => api.patch(`/todos/${id}`, changes).then((r) => r.data),
  remove: (id) => api.delete(`/todos/${id}`),
};
