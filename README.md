# Todo App — FastAPI + React 19 + PostgreSQL

A small full-stack app for learning the basic workflow:

- **Backend:** FastAPI + Pydantic, SQLAlchemy 2.0 + PostgreSQL, JWT auth with tokens stored in the DB (so logout really revokes them), CORS, custom middleware
- **Frontend:** React 19 (Vite) + axios with request/response interceptors
- **Infra:** Docker Compose runs Postgres, the backend and the frontend

```text
fast-api/
├── docker-compose.yml       # db (Postgres) + pgadmin + backend + frontend
├── pgadmin/                 # pgAdmin pre-config: servers.json + pgpass
├── backend/
│   ├── app/
│   │   ├── main.py          # app setup: lifespan (create tables), middleware, CORS, routers
│   │   ├── config.py        # settings from .env (DATABASE_URL, SECRET_KEY, origins)
│   │   ├── database.py      # SQLAlchemy engine, session, get_db dependency
│   │   ├── models.py        # SQLAlchemy models = DB tables (users, todos, tokens)
│   │   ├── schemas.py       # Pydantic models = API request/response shapes
│   │   ├── security.py      # password hashing, JWT, get_current_user dependency
│   │   ├── middleware.py    # RequestID + Timing/Logging middleware
│   │   └── routers/
│   │       ├── auth.py      # /api/auth/register, /login, /logout, /me, /sessions
│   │       └── todos.py     # /api/todos CRUD (protected)
│   ├── pyproject.toml       # uv project: dependencies + metadata
│   ├── uv.lock              # exact pinned versions (commit this)
│   ├── .python-version      # Python version uv uses
│   ├── .env.example         # copy to .env (secret key, DATABASE_URL...)
│   └── Dockerfile
├── postman/                 # API test collection + environment
└── frontend/
    ├── .env.example         # copy to .env (API URL)
    ├── Dockerfile           # multi-stage: node build -> nginx
    ├── nginx.conf
    └── src/
        ├── api/axiosClient.js      # axios instance + interceptors (JWT)
        ├── api/services.js         # authApi / todoApi functions
        ├── context/AuthContext.jsx # global login state
        ├── components/AuthForm.jsx
        ├── components/TodoList.jsx
        └── App.jsx
```

## Run it

You can run everything in Docker, or only Postgres in Docker and the backend and frontend locally. The local option is better while you're editing code, because of hot reload.

### Option A: everything in Docker

```powershell
Copy-Item backend\.env.example backend\.env   # only once, then set SECRET_KEY
docker compose up --build
```

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8000> (docs at <http://localhost:8000/docs>)
- Postgres: `localhost:5432`, user / password / database `todo` / `todo` / `todo`
- pgAdmin (database UI): <http://localhost:5050>

### Option B: Postgres in Docker, code locally

The backend uses [uv](https://docs.astral.sh/uv/) for Python and dependency management.

**Terminal 1: database**

```powershell
docker compose up -d db pgadmin   # Postgres + the pgAdmin UI
```

**Terminal 2: backend** (<http://localhost:8000>)

```powershell
cd backend
Copy-Item .env.example .env    # only once, then put a real SECRET_KEY in .env
uv sync                        # only once: creates .venv and installs from uv.lock
uv run fastapi dev app/main.py
```

Tables are created automatically on startup. `uv run` uses the project's `.venv`, so there's no `activate` step.

**Terminal 3: frontend** (<http://localhost:5173>)

```powershell
cd frontend
Copy-Item .env.example .env    # only once
npm install                    # only once
npm run dev
```

If port 8000 or 5432 is already taken (for example by Option A's containers, or a Postgres installed on Windows), stop that first: `docker compose down`.

### Handy uv commands

| Command | What it does |
|---|---|
| `uv add <pkg>` | Install a package and add it to `pyproject.toml` + `uv.lock` |
| `uv remove <pkg>` | Uninstall and remove it from the project |
| `uv sync` | Make `.venv` match `uv.lock` exactly |
| `uv run <cmd>` | Run a command inside the project environment |
| `uv tree` | Show the dependency tree |

## Environment variables

Settings are read in [config.py](backend/app/config.py). `python-dotenv` loads `backend/.env`, and real environment variables override it.

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | dev-only key | Signs JWTs. Use 32+ random bytes in real deployments |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token lifetime |
| `ALLOWED_ORIGINS` | `http://localhost:5173,...` | CORS allow-list, comma-separated |
| `DATABASE_URL` | `postgresql+psycopg://todo:todo@localhost:5432/todo` | Where the database is |
| `SQL_ECHO` | `false` | `true` prints every SQL query SQLAlchemy runs |
| `VITE_API_URL` (frontend) | `http://localhost:8000/api` | Where axios sends requests |

`.env` files are git-ignored. Only the `.env.example` files are meant to be committed.

## Database (PostgreSQL)

### Tables

```mermaid
erDiagram
    users ||--o{ todos : owns
    users ||--o{ tokens : "logs in with"

    users {
        uuid id PK
        varchar username "unique, case-insensitive"
        varchar hashed_password "PBKDF2 + salt"
        timestamptz created_at
    }
    todos {
        uuid id PK
        varchar title
        text description "nullable"
        boolean completed
        timestamptz created_at
        uuid owner_id FK "ON DELETE CASCADE"
    }
    tokens {
        varchar jti PK "JWT id claim"
        uuid user_id FK "ON DELETE CASCADE"
        timestamptz created_at
        timestamptz expires_at
        timestamptz revoked_at "null = still active"
        varchar user_agent "which browser/app"
    }
```

Two kinds of model, which is easy to mix up at first:

| | SQLAlchemy model ([models.py](backend/app/models.py)) | Pydantic schema ([schemas.py](backend/app/schemas.py)) |
|---|---|---|
| Describes | A **table** in Postgres | What the **API** accepts and returns |
| Example | `User` has `hashed_password` | `UserOut` has no `hashed_password` |
| Link | — | `from_attributes=True` lets a schema read a model object |

### Why tokens are stored in the DB

A JWT is self-contained: the server checks its signature and expiry without any lookup. That's fast, but it means a token **can't be cancelled**. It stays valid until it expires, even after the user "logs out".

Storing one row per login in `tokens` fixes that:

```mermaid
flowchart LR
    req["Request with<br/>Bearer token"] --> sig{"Signature valid<br/>and not expired?"}
    sig -- no --> e1["401 Invalid or expired token"]
    sig -- yes --> row{"tokens row for jti<br/>exists?"}
    row -- no --> e1
    row -- yes --> rev{"revoked_at<br/>is null?"}
    rev -- no --> e2["401 Token has been revoked"]
    rev -- yes --> ok["✅ request continues<br/>as token.user"]
```

- **Login** creates a row with a random `jti` and puts that `jti` inside the JWT.
- **Every request** checks the signature (no DB needed), then looks up the row.
- **Logout** sets `revoked_at`, and from then on that token gets 401.
- **`GET /api/auth/sessions`** lists your active logins, one row per device or browser.
- **Expired rows** for a user are deleted each time that user logs in.

Only the `jti` is stored, never the token string itself. If the table leaked, the rows couldn't be used to log in, the same reason passwords are stored as hashes.

### Look inside the database with pgAdmin

[pgAdmin 4](https://www.pgadmin.org/) is the standard web UI for PostgreSQL. It runs as the `pgadmin` service.

1. Open <http://localhost:5050>. There's no login page.
2. In the left sidebar, expand **Servers → Todo DB (docker) → Databases → todo → Schemas → public → Tables**. It connects without asking for a password.
3. Right-click a table → **View/Edit Data → All Rows** to see its rows. Try `tokens` before and after you log out in the app: `revoked_at` gets filled in.
4. **Tools → Query Tool** opens a SQL editor.
5. Right-click the **todo** database → **ERD For Database** draws the table relationships.

How it's wired up ([pgadmin/](pgadmin/)):

| File | Purpose |
|---|---|
| `servers.json` | Registers the "Todo DB (docker)" server on first start. Host is `db`, because pgAdmin runs inside the Docker network |
| `pgpass` | Saved password, so there's no prompt. The container copies it and makes it private, because the database client ignores password files that other users can read |

pgAdmin runs in **desktop mode** (`PGADMIN_CONFIG_SERVER_MODE: "False"`): one user and no login. That's convenient locally, but never expose port 5050 to a network.

`servers.json` is only imported the **first** time pgAdmin starts. If you change it, reset pgAdmin's settings volume:

```powershell
docker compose rm -sf pgadmin; docker volume rm fast-api_pgadmin-data; docker compose up -d pgadmin
```

**Other tools** work too, because Postgres is published on `localhost:5432` (user `todo`, password `todo`, database `todo`). For example: DBeaver, DataGrip, TablePlus, Beekeeper Studio, or the VS Code "PostgreSQL" extension. Use host `localhost` from your machine; `db` only works inside Docker.

### Look inside the database from the terminal

```powershell
docker exec -it todo-db psql -U todo -d todo
```

```sql
\dt                                   -- list tables
SELECT username, created_at FROM users;
SELECT title, completed FROM todos;
SELECT jti, revoked_at, user_agent FROM tokens;
\q                                    -- quit
```

Tables are created by `Base.metadata.create_all()` at startup. That only creates **missing** tables; it never changes an existing one. If you change a model, the simplest fix while learning is to reset the data with `docker compose down -v`. Real projects use **Alembic** migrations for this.

## Docker

### What runs where

```mermaid
flowchart LR
    subgraph host["Your computer"]
        browser["🌐 Browser"]
    end

    subgraph docker["Docker (docker compose)"]
        subgraph fe["frontend container"]
            nginx["nginx<br/>serves React build"]
        end
        subgraph be["backend container"]
            api["FastAPI<br/>fastapi run :8000"]
        end
        subgraph dbc["db container"]
            pg[("PostgreSQL 18<br/>:5432")]
        end
        subgraph pga["pgadmin container"]
            admin["pgAdmin 4"]
        end
        vol[("pgdata volume")]
    end

    browser -- "1 load page<br/>localhost:5173" --> nginx
    browser -- "2 API calls + JWT<br/>localhost:8000/api" --> api
    api -- "3 SQL<br/>host: db" --> pg
    browser -. "4 database UI<br/>localhost:5050" .-> admin
    admin -. "SQL, host: db" .-> pg
    pg --- vol
```

1. The browser downloads the React files from nginx once.
2. After that, React runs **in the browser** and calls the API directly. That's why `VITE_API_URL` is `localhost:8000` and not the Docker name `backend`, and why CORS still applies (port 5173 and port 8000 are different origins).
3. The backend talks to Postgres **inside** Docker's network, where the database's hostname is its service name, `db`. So `docker-compose.yml` overrides `DATABASE_URL` to use `@db:5432`, while your local `.env` uses `@localhost:5432`.
4. pgAdmin is a separate web app for **you**, not part of the app's request flow. It also reaches Postgres as `db`.

Startup order is enforced with health checks: `db` (`pg_isready`), then `backend` (`/api/health`), then `frontend`.

### How the images are built

| | Backend ([Dockerfile](backend/Dockerfile)) | Frontend ([Dockerfile](frontend/Dockerfile)) |
|---|---|---|
| Base | `python:3.14-slim` + uv binary | `node:24-alpine` to build, `nginx:1.29-alpine` to serve |
| Dependencies | `uv sync --locked` from `uv.lock` | `npm ci` from `package-lock.json` |
| Config | `.env` passed in at **runtime** via `env_file` | `VITE_API_URL` baked in at **build time** via `args` |
| Extras | non-root user, `HEALTHCHECK` on `/api/health` | multi-stage build, so the final image has no Node |

The database uses the official `postgres:18-alpine` image, with its data in the `pgdata` named volume.

Dependencies are copied and installed **before** the app code, so Docker caches that layer. Editing code then rebuilds in seconds instead of reinstalling everything.

### Useful Docker commands

| Command | What it does |
|---|---|
| `docker compose up --build` | Build images and start everything (add `-d` to run in the background) |
| `docker compose up -d db` | Start only Postgres |
| `docker compose up -d db pgadmin` | Start Postgres + pgAdmin |
| `docker compose logs -f backend` | Follow the backend logs (middleware timing lines show up here) |
| `docker compose ps` | Show container status, including health |
| `docker compose down` | Stop and remove containers. The data volume is kept |
| `docker compose down -v` | Also delete the `pgdata` volume, which **wipes the database** |

## Test the API with Postman

The [postman/](postman/) folder has a collection that tests the whole flow in order:

| Folder | What it checks |
|---|---|
| 0. Health | API is up |
| 1. Auth | Register (201), duplicate (409), invalid data (422), wrong password (401), login (saves the token and decodes the JWT, including `jti`), `/me`, `/sessions` |
| 2. Todos | Create, list, get, PATCH, both filters, delete, then 404 after delete |
| 3. Security | No token, garbage token and a **tampered** token all get 401. A second user can't see or delete the first user's todos |
| 4. CORS | Preflight from `localhost:5173` is allowed, one from another origin is rejected, and `expose_headers` is present |
| 5. Logout | Logout (204), then the same token gets 401 "revoked", while the other user's token still works |

A collection-level test also checks that every response carries the `X-Request-ID` and `X-Process-Time` middleware headers.

**In Postman:**

1. **Import** both files from `postman/` (the collection and the "Todo API - Local" environment).
2. Pick the **Todo API - Local** environment (top right).
3. Start the backend, then **Run collection**. Run it as a whole: each request saves values (token, todo IDs) that later requests use.

You can also send requests one by one. Run **Login** first; it saves `access_token`, and every other request inherits `Bearer {{access_token}}` from the collection's Authorization tab. Each run registers a new random user, so it can be repeated.

**From the terminal** with Newman (Postman's command-line runner):

```powershell
npx newman run postman/Todo-API.postman_collection.json -e postman/Todo-API-local.postman_environment.json
```

## How login + JWT works

```mermaid
sequenceDiagram
    participant R as React
    participant AX as axios interceptors
    participant F as FastAPI
    participant DB as PostgreSQL

    R->>F: POST /auth/login {username, password}
    F->>DB: SELECT user, verify password hash
    F->>DB: INSERT INTO tokens (jti, user_id, expires_at)
    F-->>R: { access_token }  (JWT with sub + jti + exp)
    R->>R: save token in localStorage

    R->>AX: todoApi.list()
    AX->>F: GET /todos + Authorization: Bearer token
    F->>F: check JWT signature + expiry
    F->>DB: SELECT token row by jti (exists? revoked?)
    alt token valid
        F->>DB: SELECT todos WHERE owner_id = user.id
        F-->>R: 200 [todos]
    else expired / invalid / revoked
        F-->>AX: 401
        AX->>R: clear token + "auth:logout" event → login screen
    end

    R->>F: POST /auth/logout
    F->>DB: UPDATE tokens SET revoked_at = now()
    F-->>R: 204
```

## How a request flows

Example: clicking **Add** on a todo.

```text
React (TodoList.jsx)
  └─ todoApi.create("Buy milk")                         services.js
      └─ api.post("/todos", {...})                      axiosClient.js
          └─ REQUEST INTERCEPTOR adds  Authorization: Bearer <jwt>
              │
              │  Browser: different origin (5173 -> 8000)?
              │  -> sends OPTIONS preflight first (CORS)
              ▼
FastAPI
  CORSMiddleware            answers preflight, adds Access-Control-* headers
  RequestIDMiddleware       request.state.request_id = "a1b2c3d4"
  TimingLoggingMiddleware   starts a timer
  @app.middleware("http")   adds X-Powered-By
  Router: POST /api/todos
    ├─ Pydantic validates body (TodoCreate)        -> 422 if invalid
    ├─ Depends(get_db) opens a DB session
    ├─ Depends(get_current_user) checks JWT + tokens table -> 401 if bad/revoked
    └─ db.add(Todo(...)); db.commit()              -> INSERT INTO todos ...
  response_model=TodoOut shapes the JSON
  session closed (end of get_db)
              │
              ▼  (middleware runs again in reverse, adding headers)
axios RESPONSE INTERCEPTOR
  ├─ success: logs timing + X-Request-ID to the console
  └─ error:   401 -> clear token + fire "auth:logout" event
              any -> turn FastAPI's `detail` into error.message
React updates state -> UI re-renders
```

## Concepts to explore

| Concept | Where | Try this |
|---|---|---|
| Pydantic validation | `schemas.py` | Register with a 2-char username and look at the 422 |
| response_model filtering | `routers/auth.py` | `hashed_password` is in the `users` table but never in responses |
| Dependency injection | `security.py` → `get_current_user` | Call `/api/todos` in /docs without "Authorize" |
| DB session per request | `database.py` → `get_db` | Set `SQL_ECHO=true` and watch the SQL for each request |
| ORM queries | `routers/todos.py` | Compare the `select(...)` code with the SQL printed by `SQL_ECHO` |
| JWT | `security.py` | Paste a token into jwt.io to see `sub`, `jti` and `exp` |
| Token revocation | `security.py` + `tokens` table | Copy your token, log out, then call `/api/auth/me` with it in /docs |
| Sessions | `/api/auth/sessions` | Log in from two browsers and list both sessions |
| Middleware order | `main.py` | Check the `X-Request-ID` / `X-Process-Time` headers in DevTools |
| CORS | `main.py` | Remove `5173` from `ALLOWED_ORIGINS`; the browser blocks the call |
| CORS expose_headers | `main.py` + `axiosClient.js` | Remove `expose_headers`; the console log shows `undefined` |
| Request interceptor | `axiosClient.js` | Token is attached automatically to every call |
| Response interceptor | `axiosClient.js` | Edit the token in localStorage, refresh, and you are logged out |

## API

| Method | Path | Auth | Body |
|---|---|---|---|
| POST | `/api/auth/register` | — | `{username, password}` |
| POST | `/api/auth/login` | — | `{username, password}` → `{access_token}` |
| POST | `/api/auth/logout` | ✅ | — (revokes the current token) |
| GET | `/api/auth/me` | ✅ | — |
| GET | `/api/auth/sessions` | ✅ | — (active logins from the `tokens` table) |
| GET | `/api/todos?completed=true` | ✅ | — |
| POST | `/api/todos` | ✅ | `{title, description?}` |
| GET | `/api/todos/{id}` | ✅ | — |
| PATCH | `/api/todos/{id}` | ✅ | `{title?, description?, completed?}` |
| DELETE | `/api/todos/{id}` | ✅ | — |
