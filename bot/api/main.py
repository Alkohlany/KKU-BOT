from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bot.api.routes import auth, responses, groups, users, stats, news, questions, scheduled_posts, study_plans

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


@app.get("/")
async def root():
    return {"message": "KKU Bot Dashboard API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
