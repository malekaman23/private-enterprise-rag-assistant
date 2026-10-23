"""Quarantine and admin approval workflow for employee document uploads."""

import json
import os
import sqlite3
from datetime import datetime, timezone

import storage

SUBMISSIONS_DB = "memory/document_submissions.db"


def _connect():
    os.makedirs(os.path.dirname(SUBMISSIONS_DB), exist_ok=True)
    conn = sqlite3.connect(SUBMISSIONS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            quarantine_path TEXT NOT NULL,
            category TEXT NOT NULL,
            department_id TEXT NOT NULL DEFAULT '',
            required_role TEXT NOT NULL DEFAULT 'shared',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewed_by TEXT,
            review_note TEXT
        )
    """)
    return conn


def _table():
    if not storage.enabled():
        return None
    storage.init()
    return storage.table("document_submissions")


def create(tenant_id, user_id, filename, quarantine_path, category, department_id, required_role):
    now = datetime.now(timezone.utc)
    table = _table()
    if table is not None:
        with storage.init().begin() as conn:
            result = conn.execute(table.insert().values(
                tenant_id=tenant_id, user_id=user_id, filename=filename,
                quarantine_path=quarantine_path, category=category,
                department_id=department_id, required_role=required_role,
                status="pending", created_at=now,
            ))
            return int(result.inserted_primary_key[0])
    conn = _connect()
    cur = conn.execute("""INSERT INTO document_submissions
        (tenant_id,user_id,filename,quarantine_path,category,department_id,required_role,created_at)
        VALUES (?,?,?,?,?,?,?,?)""", (tenant_id, user_id, filename, quarantine_path,
        category, department_id, required_role, now.isoformat()))
    conn.commit(); submission_id = cur.lastrowid; conn.close()
    return submission_id


def _row(row):
    if hasattr(row, "_mapping"):
        value = dict(row._mapping)
        for key in ("created_at", "reviewed_at"):
            if value.get(key) and hasattr(value[key], "isoformat"):
                value[key] = value[key].isoformat()
        return value
    return {"id": row[0], "tenant_id": row[1], "user_id": row[2], "filename": row[3],
            "quarantine_path": row[4], "category": row[5], "department_id": row[6],
            "required_role": row[7], "status": row[8], "created_at": row[9],
            "reviewed_at": row[10], "reviewed_by": row[11], "review_note": row[12]}


def list_for(tenant_id, user_id=None, include_completed=False):
    table = _table()
    if table is not None:
        from sqlalchemy import select
        condition = table.c.tenant_id == tenant_id
        if user_id:
            condition = condition & (table.c.user_id == user_id)
        if not include_completed:
            condition = condition & (table.c.status == "pending")
        with storage.init().connect() as conn:
            rows = conn.execute(select(table).where(condition).order_by(table.c.id.desc())).fetchall()
        return [_row(row) for row in rows]
    conn = _connect()
    query = "SELECT id,tenant_id,user_id,filename,quarantine_path,category,department_id,required_role,status,created_at,reviewed_at,reviewed_by,review_note FROM document_submissions WHERE tenant_id=?"
    params = [tenant_id]
    if user_id:
        query += " AND user_id=?"; params.append(user_id)
    if not include_completed:
        query += " AND status='pending'"
    query += " ORDER BY id DESC"
    rows = conn.execute(query, params).fetchall(); conn.close()
    return [_row(row) for row in rows]


def get(submission_id, tenant_id):
    rows = list_for(tenant_id, include_completed=True)
    return next((row for row in rows if int(row["id"]) == int(submission_id)), None)


def review(submission_id, tenant_id, status, reviewed_by, note=""):
    if status not in {"approved", "rejected"}:
        raise ValueError("Invalid review status")
    now = datetime.now(timezone.utc)
    table = _table()
    if table is not None:
        with storage.init().begin() as conn:
            result = conn.execute(table.update().where(
                table.c.id == submission_id, table.c.tenant_id == tenant_id,
                table.c.status == "pending",
            ).values(status=status, reviewed_at=now, reviewed_by=reviewed_by, review_note=note))
        return result.rowcount == 1
    conn = _connect()
    cur = conn.execute("""UPDATE document_submissions SET status=?,reviewed_at=?,reviewed_by=?,review_note=?
        WHERE id=? AND tenant_id=? AND status='pending'""",
        (status, now.isoformat(), reviewed_by, note, submission_id, tenant_id))
    conn.commit(); changed = cur.rowcount; conn.close()
    return changed == 1
