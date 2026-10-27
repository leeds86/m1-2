"""Same JSON-document contract for Firestore and explicit local SQLite mode."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.errors import AppError


class SQLiteStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("CREATE TABLE IF NOT EXISTS documents (collection TEXT, id TEXT, "
                       "market TEXT, owner TEXT, payload TEXT NOT NULL, PRIMARY KEY(collection, id))")
            db.execute("CREATE INDEX IF NOT EXISTS document_market ON documents(collection, market)")
            db.execute("CREATE INDEX IF NOT EXISTS document_owner ON documents(collection, owner)")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, collection, doc_id, payload):
        try:
            with self.connection() as db:
                db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
                           (collection, doc_id, payload.get("market"), payload.get("owner"),
                            json.dumps(payload, ensure_ascii=False)))
        except sqlite3.IntegrityError:
            raise AppError(409, "같은 종목·날짜의 데이터가 이미 있습니다.") from None
        return payload

    def get(self, collection, doc_id):
        with self.connection() as db:
            row = db.execute("SELECT payload FROM documents WHERE collection=? AND id=?",
                             (collection, doc_id)).fetchone()
        if not row:
            raise AppError(404, "기록을 찾을 수 없습니다.")
        return json.loads(row[0])

    def list(self, collection, field, value):
        if field not in {"market", "owner"}:
            raise ValueError("Unsupported document filter")
        with self.connection() as db:
            rows = db.execute(f"SELECT payload FROM documents WHERE collection=? AND {field}=?",
                              (collection, value)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def mutate(self, collection, doc_id, transform):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM documents WHERE collection=? AND id=?",
                             (collection, doc_id)).fetchone()
            if not row:
                raise AppError(404, "기록을 찾을 수 없습니다.")
            payload = transform(json.loads(row[0]))
            if payload is None:
                db.execute("DELETE FROM documents WHERE collection=? AND id=?", (collection, doc_id))
            else:
                db.execute("UPDATE documents SET market=?, owner=?, payload=? WHERE collection=? AND id=?",
                           (payload.get("market"), payload.get("owner"), json.dumps(payload, ensure_ascii=False),
                            collection, doc_id))
        return payload


class FirestoreStore:
    def __init__(self, settings):
        import firebase_admin
        from firebase_admin import credentials, firestore

        try:
            app = firebase_admin.get_app("coin-assistant")
        except ValueError:
            if settings.firebase_json:
                credential = credentials.Certificate(json.loads(settings.firebase_json))
            elif settings.firebase_path:
                credential = credentials.Certificate(settings.firebase_path)
            else:
                raise AppError(503, "Firebase 서비스 계정 환경변수를 설정하세요.")
            app = firebase_admin.initialize_app(credential, name="coin-assistant")
        self.client = firestore.client(app=app)

    def create(self, collection, doc_id, payload):
        from google.api_core.exceptions import AlreadyExists

        try:
            self.client.collection(collection).document(doc_id).create(payload, timeout=15)
        except AlreadyExists:
            raise AppError(409, "같은 종목·날짜의 데이터가 이미 있습니다.") from None
        return payload

    def get(self, collection, doc_id):
        snapshot = self.client.collection(collection).document(doc_id).get(timeout=15)
        if not snapshot.exists:
            raise AppError(404, "기록을 찾을 수 없습니다.")
        return snapshot.to_dict()

    def list(self, collection, field, value):
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self.client.collection(collection).where(filter=FieldFilter(field, "==", value))
        return [snapshot.to_dict() for snapshot in query.stream(timeout=15)]

    def mutate(self, collection, doc_id, transform):
        from google.cloud import firestore
        from google.api_core.exceptions import Aborted

        reference = self.client.collection(collection).document(doc_id)

        @firestore.transactional
        def apply(transaction):
            snapshot = reference.get(transaction=transaction, timeout=15)
            if not snapshot.exists:
                raise AppError(404, "기록을 찾을 수 없습니다.")
            payload = transform(snapshot.to_dict())
            if payload is None:
                transaction.delete(reference)
            else:
                transaction.set(reference, payload)
            return payload

        try:
            return apply(self.client.transaction(max_attempts=3))
        except ValueError as error:
            # Only the SDK's exhausted Aborted retry is a data conflict.
            if isinstance(error.__cause__, Aborted):
                raise AppError(409, "동시 수정으로 저장이 충돌했습니다. 새로고침 후 다시 시도하세요.") from None
            raise
