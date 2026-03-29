from fastapi import APIRouter, Query, HTTPException, Body
from typing import Any
import psycopg2.extras
from db import get_conn

router = APIRouter(prefix="/api")


@router.get("/words")
def get_words(
    part_of_speech: str = Query(None),
    language_code: str = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    filters = []
    params = []

    if part_of_speech:
        filters.append("pos = %s")
        params.append(part_of_speech)
    if language_code:
        filters.append("language_code = %s")
        params.append(language_code)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    params_count = params.copy()
    params += [limit, offset]

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT COUNT(*) FROM words {where}", params_count)
            total = cur.fetchone()["count"]

            cur.execute(
                f"SELECT id, word, def_en, pos, class, language_code, etymology "
                f"FROM words {where} ORDER BY word LIMIT %s OFFSET %s",
                params,
            )
            rows = cur.fetchall()

    return {"total": total, "words": [dict(r) for r in rows]}


@router.get("/words/{word_id}")
def get_word(word_id: int):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, word, word_scripted, def_en, pos, class, language_code, etymology, tags, example FROM words WHERE id = %s",
                (word_id,),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Word not found")
    lang_code = row["language_code"]
    pos = row["pos"]
    class_ = row["class"]
    # grammar tables that apply to this word
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, table_name, apply_on, row_order, col_order, data
                FROM grammar_tables
                WHERE target_language = %s AND (apply_on IS NULL OR CONCAT('/', apply_on, '/') LIKE ANY (ARRAY[%s, %s]))
            """, (lang_code, f"/{pos}/", f"/{pos}[{class_}]/"))
            grammar_tables = cur.fetchall()
    row["grammar_tables"] = [dict(t) for t in grammar_tables]
    return dict(row)


_WORD_FIELDS = {'word', 'word_scripted', 'def_en', 'pos', 'class', 'language_code', 'etymology', 'tags', 'example'}

@router.put("/words/{word_id}")
def update_word(word_id: int, body: dict[str, Any] = Body(...)):
    updates = {k: v for k, v in body.items() if k in _WORD_FIELDS}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    set_clause = ', '.join(f'"{k}" = %s' for k in updates)
    values = list(updates.values()) + [word_id]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f'UPDATE words SET {set_clause} WHERE id = %s', values)
            affected = cur.rowcount
    if affected == 0:
        raise HTTPException(status_code=404, detail="Word not found")
    return {"ok": True}


@router.delete("/words/{word_id}")
def delete_word(word_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM words WHERE id = %s", (word_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Word not found")
    return {"ok": True}


@router.post("/words", status_code=201)
def create_word(body: dict[str, Any] = Body(...)):
    fields = {k: v for k, v in body.items() if k in _WORD_FIELDS}
    if 'word' not in fields:
        raise HTTPException(status_code=400, detail="'word' is required")
    cols = ', '.join(f'"{k}"' for k in fields)
    placeholders = ', '.join('%s' for _ in fields)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f'INSERT INTO words ({cols}) VALUES ({placeholders}) RETURNING id',
                list(fields.values()),
            )
            new_id = cur.fetchone()[0]
    return {"id": new_id}


@router.get("/filters")
def get_filters():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT code FROM parts_of_speech WHERE code IS NOT NULL ORDER BY 1")
            parts = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT code FROM langs WHERE code IS NOT NULL ORDER BY 1")
            langs = [r[0] for r in cur.fetchall()]
    return {"parts_of_speech": parts, "language_codes": langs}


@router.get("/default/lang")
def get_default_lang():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT language_code, COUNT(*) as word_count
                FROM words
                WHERE language_code IS NOT NULL
                GROUP BY language_code
                ORDER BY word_count DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                return {"language_code": row[0], "word_count": row[1]}
            cur.execute("SELECT code FROM langs ORDER BY code LIMIT 1")
            first_lang = cur.fetchone()
            if first_lang:
                return {"language_code": first_lang[0], "word_count": 0}
            return {"language_code": None, "word_count": 0}


@router.get("/search")
def search_words(
    query: str = Query(..., min_length=1),
    target: str = Query("all", regex="^(words|definitions|tags|all)$"),
    limit: int = Query(20, le=100),
    pos: str = Query(None),
    language_code: str = Query(None)
):
    print(f"Search query: '{query}', target: '{target}', limit: {limit}")  # Debug log
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            filter = ''
            if pos:
                filter += f" AND pos = '{pos}'"
            if language_code:
                filter += f" AND language_code = '{language_code}'"
            if target == "words":
                cur.execute("SELECT id, word, def_en, pos, class, language_code FROM words WHERE word ILIKE %s" + filter + " ORDER BY word LIMIT %s", (f"%{query}%", limit))
            elif target == "definitions":
                cur.execute("SELECT id, word, def_en, pos, class, language_code FROM words WHERE def_en ILIKE %s" + filter + " ORDER BY word LIMIT %s", (f"%{query}%", limit))
            elif target == "tags":
                cur.execute("SELECT id, word, def_en, pos, class, language_code FROM words WHERE tags ILIKE %s ORDER BY word LIMIT %s", (f"%{query}%", limit))
            else:  # all
                cur.execute("""
                    SELECT id, word, def_en, pos, class, language_code
                    FROM words
                    WHERE word ILIKE %s OR def_en ILIKE %s OR tags ILIKE %s
                    ORDER BY word
                    LIMIT %s
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
            rows = cur.fetchall()
    return {"results": [dict(r) for r in rows]}
