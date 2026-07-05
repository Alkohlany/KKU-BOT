from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from bot.api.routes import auth, responses, groups, users, stats, news, questions, scheduled_posts, study_plans
import os

app = FastAPI(title="KKU Bot Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy"}


app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(responses.router, prefix="/api/responses", tags=["Responses"])
app.include_router(groups.router, prefix="/api/groups", tags=["Groups"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(questions.router, prefix="/api/questions", tags=["Questions"])
app.include_router(scheduled_posts.router, prefix="/api/scheduled-posts", tags=["Scheduled Posts"])
app.include_router(study_plans.router, prefix="/api/study-plans", tags=["Study Plans"])


DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "dashboard", "dist")

if os.path.exists(DASHBOARD_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DASHBOARD_DIR, "assets")), name="assets")

    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404 and not request.url.path.startswith("/api"):
            index_path = os.path.join(DASHBOARD_DIR, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
else:
    @app.get("/")
    async def root():
        return {"message": "KKU Bot Dashboard API"}
