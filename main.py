from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers import words, langs, phonology

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(words.router)
app.include_router(langs.router)
app.include_router(phonology.router)


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

# Serve static assets
app.mount("/", StaticFiles(directory="site", html=True), name="static")
