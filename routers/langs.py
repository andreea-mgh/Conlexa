from fastapi import APIRouter, HTTPException, Body
from typing import Any
import psycopg2
import psycopg2.extras
from db import get_conn

router = APIRouter(prefix="/api")


@router.get("/langs")
def get_langs():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT code, name_en, ipa_ruleset FROM langs ORDER BY code")
            rows = cur.fetchall()
    return {"langs": [dict(r) for r in rows]}


@router.get("/langs/{lang_code}")
def get_lang(lang_code: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT code, name_en, ipa_ruleset FROM langs WHERE code = %s", (lang_code,))
            row = cur.fetchone()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT code, name_en FROM parts_of_speech WHERE language_code = %s",
                (lang_code,),
            )
            pos_rows = cur.fetchall()
            row["parts_of_speech"] = [dict(r) for r in pos_rows]
    if row is None:
        raise HTTPException(status_code=404, detail="Language not found")
    return dict(row)


@router.put("/langs/{lang_code}")
def update_lang(lang_code: str, body: dict[str, Any] = Body(...)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE langs SET ipa_ruleset = %s WHERE code = %s",
                (body.get("ipa_ruleset"), lang_code),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Language not found")
    return {"ok": True}


@router.post("/langs/{lang_code}/parts_of_speech", status_code=201)
def add_part_of_speech(lang_code: str, body: dict[str, Any] = Body(...)):
    code = body.get("code")
    name_en = body.get("name_en")
    if not code or not name_en:
        raise HTTPException(status_code=400, detail="'code' and 'name_en' are required")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM langs WHERE code = %s", (lang_code,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Language not found")
            try:
                cur.execute(
                    "INSERT INTO parts_of_speech (language_code, code, name_en) VALUES (%s, %s, %s)",
                    (lang_code, code, name_en),
                )
            except psycopg2.IntegrityError:
                raise HTTPException(status_code=400, detail="Part of speech code already exists for this language")
    return {"ok": True}


@router.delete("/langs/{lang_code}/parts_of_speech/{pos_code}")
def delete_part_of_speech(lang_code: str, pos_code: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM words WHERE language_code = %s AND pos = %s",
                (lang_code, pos_code),
            )
            if cur.fetchone() is not None:
                raise HTTPException(status_code=400, detail="Part of speech is in use by existing words.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM parts_of_speech WHERE language_code = %s AND code = %s",
                (lang_code, pos_code),
            )
    return {"ok": True}


@router.get("/langs/{lang_code}/grammar_tables")
def get_grammar_tables(lang_code: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM grammar_tables WHERE target_language = %s",
                (lang_code,),
            )
            return [dict(r) for r in cur.fetchall()]


@router.post("/langs/{lang_code}/grammar_tables", status_code=201)
def create_grammar_table(lang_code: str, body: dict[str, Any] = Body(...)):
    table_name = body.get("table_name")
    apply_on = body.get("apply_on")
    row_order = body.get("row_order")
    col_order = body.get("col_order")
    data = body.get("data")
    ## TODO: make able to post table with empty data, fill later
    if not table_name or not data:
        raise HTTPException(status_code=400, detail="'table_name' and 'data' are required")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM langs WHERE code = %s", (lang_code,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Language not found")
            cur.execute(
                "INSERT INTO grammar_tables (target_language, table_name, apply_on, row_order, col_order, data) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (lang_code, table_name, apply_on, row_order, col_order, psycopg2.extras.Json(data)),
            )
            new_id = cur.fetchone()[0]
    return {"id": new_id}


@router.get("/grammar_tables/{table_id}")
def get_grammar_table(table_id: int):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM grammar_tables WHERE id = %s",
                (table_id,),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Grammar table not found")
    return dict(row)


@router.put("/grammar_tables/{table_id}")
def update_grammar_table(table_id: int, body: dict[str, Any] = Body(...)):
    table_name = body.get("table_name")
    apply_on = body.get("apply_on")
    row_order = body.get("row_order")
    col_order = body.get("col_order")
    data = body.get("data")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM grammar_tables WHERE id = %s", (table_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Grammar table not found")
            cur.execute(
                "UPDATE grammar_tables SET table_name = %s, apply_on = %s, row_order = %s, col_order = %s, data = %s WHERE id = %s",
                (table_name, apply_on, row_order, col_order, psycopg2.extras.Json(data), table_id),
            )
    return {"ok": True}
