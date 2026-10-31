"""
CRUD for todos. Every route depends on get_current_user, so:
  - no/invalid/revoked token -> 401
  - users only ever see/modify their OWN todos (filtered by owner_id)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Todo, User
from ..schemas import TodoCreate, TodoOut, TodoUpdate
from ..security import get_current_user

router = APIRouter(prefix="/api/todos", tags=["todos"])


def _find_own_todo(db: Session, todo_id: uuid.UUID, user: User) -> Todo:
    todo = db.get(Todo, todo_id)  # lookup by primary key
    if todo is None or todo.owner_id != user.id:
        # 404 (not 403) so we don't even reveal that the todo exists
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Todo not found")
    return todo


@router.get("", response_model=list[TodoOut])
def list_todos(
    completed: bool | None = Query(default=None, description="Filter by status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Builds:  SELECT * FROM todos WHERE owner_id = ? [AND completed = ?]
    #          ORDER BY created_at DESC
    query = select(Todo).where(Todo.owner_id == user.id)
    if completed is not None:
        query = query.where(Todo.completed == completed)
    return db.scalars(query.order_by(Todo.created_at.desc())).all()


@router.post("", response_model=TodoOut, status_code=status.HTTP_201_CREATED)
def create_todo(body: TodoCreate, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    todo = Todo(**body.model_dump(), owner_id=user.id)  # pydantic model -> dict -> row
    db.add(todo)
    db.commit()
    return todo


# `todo_id: uuid.UUID` -> FastAPI returns 422 for a malformed id, before any DB query
@router.get("/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: uuid.UUID, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    return _find_own_todo(db, todo_id, user)


@router.patch("/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: uuid.UUID, body: TodoUpdate,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = _find_own_todo(db, todo_id, user)
    # exclude_unset=True -> only fields the client actually sent
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)
    db.commit()  # SQLAlchemy tracked the changes and issues an UPDATE
    return todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: uuid.UUID, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    db.delete(_find_own_todo(db, todo_id, user))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
