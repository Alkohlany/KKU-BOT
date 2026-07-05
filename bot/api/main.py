from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(DASHBOARD_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(DASHBOARD_DIR, "index.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "KKU Bot Dashboard API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
