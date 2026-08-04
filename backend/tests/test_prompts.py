from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Prompt
from app.routers.prompts import update_prompt
from app.schemas import PromptUpdate


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_update_prompt_supports_knowledge_update():
    db = make_session()
    db.add(Prompt(type="knowledge_update", content="old", is_active=True))
    db.commit()

    updated = update_prompt("knowledge_update", PromptUpdate(content="new"), db=db)

    assert updated.type == "knowledge_update"
    assert updated.content == "new"


def test_update_prompt_rejects_unknown_type():
    db = make_session()

    try:
        update_prompt("unknown", PromptUpdate(content="new"), db=db)
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("Expected HTTPException")
