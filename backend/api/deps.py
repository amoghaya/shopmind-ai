from fastapi import Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db


def db_session(db: Session = Depends(get_db)) -> Session:
    return db

