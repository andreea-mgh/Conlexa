from fastapi import FastAPI, Query, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import psycopg2
import psycopg2.extras
import os
from typing import Any

from wordshift import apply_ruleset

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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

# GRAMMAR TABLES

@app.get("/api/langs/{lang_code}/grammar_tables")
def get_grammar_tables(lang_code: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM grammar_tables WHERE target_language = %s",
                (lang_code,),
            )
            return [dict(r) for r in cur.fetchall()]

@app.post("/api/langs/{lang_code}/grammar_tables", status_code=201)
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
            # Check if language exists
            cur.execute("SELECT 1 FROM langs WHERE code = %s", (lang_code,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Language not found")
            # Insert new grammar table
            cur.execute(
                "INSERT INTO grammar_tables (target_language, table_name, apply_on, row_order, col_order, data) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (lang_code, table_name, apply_on, row_order, col_order, psycopg2.extras.Json(data)),
            )
            new_id = cur.fetchone()[0]
    return {"id": new_id}


@app.get("/api/grammar_tables/{table_id}")
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

@app.put("/api/grammar_tables/{table_id}")
def update_grammar_table(table_id: int, body: dict[str, Any] = Body(...)):
    table_name = body.get("table_name")
    apply_on = body.get("apply_on")
    row_order = body.get("row_order")
    col_order = body.get("col_order")
    data = body.get("data")
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check if grammar table exists
            cur.execute("SELECT 1 FROM grammar_tables WHERE id = %s", (table_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Grammar table not found")
            # Update grammar table
            cur.execute(
                "UPDATE grammar_tables SET table_name = %s, apply_on = %s, row_order = %s, col_order = %s, data = %s WHERE id = %s",
                (table_name, apply_on, row_order, col_order, psycopg2.extras.Json(data), table_id),
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

@app.get("/api/default/lang")
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
            # If no words, return the first language alphabetically
            cur.execute("SELECT code FROM langs ORDER BY code LIMIT 1")
            first_lang = cur.fetchone()
            if first_lang:
                return {"language_code": first_lang[0], "word_count": 0}
            return {"language_code": None, "word_count": 0}


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

@app.get("/api/search")
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
                cur.execute("SELECT id, word, def_en, pos, class, language_code FROM words WHERE def_en ILIKE %s" + filter + " ORDER BY word LIMIT %s", (f"%{query}%",  limit))
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






# Frontend routes

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/add")
def add_page(request: Request):
    return templates.TemplateResponse(request, "add.html")

@app.get("/dictionary")
def dictionary(request: Request):
    return templates.TemplateResponse(request, "dict.html")

@app.get("/word/{word_id}")
def word_page(request: Request, word_id: int):
    return templates.TemplateResponse(request, "word.html")

@app.get("/phono/ipa")
def ipa_index(request: Request):
    return templates.TemplateResponse(request, "ipa.html")

@app.get("/phono/ipa/documentation")
def ipa_docs(request: Request):
    return templates.TemplateResponse(request, "ipa_doc.html")

@app.get("/phono/ipa/{lang_code}")
def ipa_page(request: Request, lang_code: str):
    return templates.TemplateResponse(request, "ipa.html")

@app.get("/langs")
def lang_index(request: Request):
    return templates.TemplateResponse(request, "langs.html")

@app.get("/langs.html")
def lang_index_html(request: Request):
    return templates.TemplateResponse(request, "langs.html")

@app.get("/grammar-table.html")
def grammar_table(request: Request):
    return templates.TemplateResponse(request, "grammar-table.html")

@app.get("/ipa_doc.html")
def ipa_doc_html(request: Request):
    return templates.TemplateResponse(request, "ipa_doc.html")

# Serve frontend
app.mount("/", StaticFiles(directory="site", html=True), name="static")