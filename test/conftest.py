"""
Фікстури для тестів.

Тести працюють проти РЕАЛЬНОЇ БД, налаштованої через DATABASE_URL (.env) -
так само, як і сам застосунок (схема має бути вже застосована: sql/schema.sql
+ sql/seed_ranks.sql, або одразу sql/dump.sql).

Ізоляція тестів одне від одного забезпечується не окремою тестовою БД,
а класичним прийомом SQLAlchemy: кожен тест отримує сесію, прив'язану
до одного connection з відкритою зовнішньою транзакцією + SAVEPOINT.
Що б тест не зробив (включно з власними session.commit() усередині
коду застосунку - там, де в match_service.py/crud/*.py викликається
db.commit()) - усе відкочується в fixture-teardown (transaction.rollback()),
і реальні дані в БД лишаються незмінними.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.database import engine, get_db
from app.main import app


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()

    from sqlalchemy.orm import sessionmaker
    TestingSessionLocal = sessionmaker(bind=connection)
    session = TestingSessionLocal()

    # Кожен внутрішній db.commit() у коді застосунку насправді закриває лише
    # SAVEPOINT - одразу після цього відкриваємо новий, щоб транзакція тесту
    # (зовнішня) лишалась відкритою до явного rollback() у teardown.
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
