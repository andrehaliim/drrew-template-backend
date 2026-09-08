from fastapi import APIRouter, Depends, HTTPException, status
from app.routers.auth import get_current_user
from sqlalchemy.orm import Session
from app.models import User, Notes
from app.database import get_db
from app.schemas import NoteCreate, NoteResponse, NoteUpdate
from typing import List

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get("/", response_model=List[NoteResponse])
def list_notes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notes = (
        db.query(Notes)
        .filter(Notes.user_id == current_user.id)
        .order_by(Notes.updated_at.desc())
        .all()
    )
    return notes


@router.get("/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = (
        db.query(Notes)
        .filter(Notes.id == note_id, Notes.user_id == current_user.id)
        .first()
    )

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    return note

@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    note_data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_note = Notes(
        user_id=current_user.id,
        title=note_data.title,
        content=note_data.content,
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)

    return new_note

@router.patch("/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: int,
    note_data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = (
        db.query(Notes)
        .filter(Notes.id == note_id, Notes.user_id == current_user.id)
        .first()
    )

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    update_data = note_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)

    db.commit()
    db.refresh(note)

    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = (
        db.query(Notes)
        .filter(Notes.id == note_id, Notes.user_id == current_user.id)
        .first()
    )

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    db.delete(note)
    db.commit()

    return {"message": "Note berhasil dihapus."}    
