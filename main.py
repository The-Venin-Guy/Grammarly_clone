import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes.analyze import router as analyze_router
from routes.reset import router as reset_router
from grammar_model import BASE_URL
from routes.spellcheck import router as spellcheck_router
from routes.grammar_check import router as grammar_check_router
from routes.analyze_tone import router as analyze_tone_router
from routes.transform import router as transform_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with httpx.AsyncClient() as client:
            await client.get(BASE_URL, timeout=5.0)
        print("[startup] Server reachable — server ready.")
    except Exception:
        print("[startup] WARNING: Ollama not reachable. Generative features will fail.")
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(analyze_router)
app.include_router(reset_router)
app.include_router(spellcheck_router)
app.include_router(grammar_check_router)
app.include_router(analyze_tone_router)
app.include_router(transform_router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")