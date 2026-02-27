from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import psycopg2
import psycopg2.extras
import os
from typing import Any

from wordshift import apply_ruleset

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", 5432),
    "dbname": os.getenv("DB_NAME", "conlang"),
    "user": os.getenv("DB_USER", "conlexa"),
    "password": os.getenv("DB_PASSWORD", "password"),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)


@app.get("/api/words")
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


@app.get("/api/words/{word_id}")
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
    return dict(row)


_WORD_FIELDS = {'word', 'word_scripted', 'def_en', 'pos', 'class', 'language_code', 'etymology', 'tags', 'example'}

@app.put("/api/words/{word_id}")
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


@app.delete("/api/words/{word_id}")
def delete_word(word_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM words WHERE id = %s", (word_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Word not found")
    return {"ok": True}


@app.post("/api/words", status_code=201)
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

@app.get("/api/langs")
def get_langs():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT code, name_en, ipa_ruleset FROM langs ORDER BY code")
            rows = cur.fetchall()
    return {"langs": [dict(r) for r in rows]}

@app.get("/api/langs/{lang_code}")
def get_lang(lang_code: str):
    with get_conn() as conn:
        # get lang details
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT code, name_en, ipa_ruleset FROM langs WHERE code = %s", (lang_code,))
            row = cur.fetchone()
        # fetch associated parts of speech
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


@app.put("/api/langs/{lang_code}")
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

@app.post("/api/langs/{lang_code}/parts_of_speech", status_code=201)
def add_part_of_speech(lang_code: str, body: dict[str, Any] = Body(...)):
    code = body.get("code")
    name_en = body.get("name_en")
    if not code or not name_en:
        raise HTTPException(status_code=400, detail="'code' and 'name_en' are required")
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check if language exists
            cur.execute("SELECT 1 FROM langs WHERE code = %s", (lang_code,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Language not found")
            # Insert new part of speech
            try:
                cur.execute(
                    "INSERT INTO parts_of_speech (language_code, code, name_en) VALUES (%s, %s, %s)",
                    (lang_code, code, name_en),
                )
            except psycopg2.IntegrityError:
                raise HTTPException(status_code=400, detail="Part of speech code already exists for this language")
    return {"ok": True}

@app.delete("/api/langs/{lang_code}/parts_of_speech/{pos_code}")
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

@app.get("/api/filters")
def get_filters():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT code FROM parts_of_speech WHERE code IS NOT NULL ORDER BY 1")
            parts = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT code FROM langs WHERE code IS NOT NULL ORDER BY 1")
            langs = [r[0] for r in cur.fetchall()]
    return {"parts_of_speech": parts, "language_codes": langs}


@app.get("/api/phonology/apply")
def apply_phonology(
    word: str = Query(...),
    lang_code: str = Query(...),
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ipa_ruleset FROM langs WHERE code = %s", (lang_code,))
            row = cur.fetchone()
            # print("Fetched ruleset for language:", lang_code, row)  # Debug log
    if row is None:
        raise HTTPException(status_code=404, detail="Language not found")
    ruleset = row[0]
    if not ruleset:
        raise HTTPException(status_code=400, detail="No IPA ruleset for this language")
    try:
        result = apply_ruleset(ruleset, word)
        return {"result": result}
    except Exception as e:
        print(f"Error applying IPA rules for language {lang_code} on word '{word}': {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=f"Error applying IPA rules: {str(e)}")


@app.get("/add")
def add_page():
    return FileResponse("site/add.html")


@app.get("/dictionary")
def dictionary():
    return FileResponse("site/dict.html")


@app.get("/word/{word_id}")
def word_page(word_id: int):
    return FileResponse("site/word.html")

@app.get("/phono/ipa")
def ipa_index():
    return FileResponse("site/ipa.html")

@app.get("/phono/ipa/documentation")
def ipa_docs():
    return FileResponse("site/ipa_doc.html")

@app.get("/phono/ipa/{lang_code}")
def ipa_page(lang_code: str):
    return FileResponse("site/ipa.html")

@app.get("/langs")
def lang_index():
    return FileResponse("site/langs.html")

# Serve frontend
app.mount("/", StaticFiles(directory="site", html=True), name="static")