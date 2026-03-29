from fastapi import APIRouter, Query, HTTPException
import psycopg2.extras
from db import get_conn
from wordshift import apply_ruleset

router = APIRouter(prefix="/api/phonology")


@router.get("/apply")
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
