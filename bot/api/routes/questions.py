from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.services.database import add_question, get_all_questions, search_question, delete_question, increment_question_usage, update_question as db_update_question, get_db

router = APIRouter()

class QuestionCreate(BaseModel):
    question: str
    answer: str
    keywords: Optional[str] = None
    news_id: Optional[int] = None


@router.get("")
async def get_questions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    from bot.models.models import Question
    total = (await db.execute(select(func.count(Question.id)).where(Question.is_active == True))).scalar() or 0
    result = await db.execute(
        select(Question).where(Question.is_active == True).offset((page - 1) * limit).limit(limit)
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": q.id,
                "question": q.question,
                "answer": q.answer,
                "keywords": q.keywords,
                "news_id": q.news_id,
            }
            for q in items
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.post("")
async def create_question(data: QuestionCreate):
    q = await add_question(question=data.question, answer=data.answer,
                           category=None, keywords=data.keywords, news_id=data.news_id)
    return {"id": q.id, "question": q.question, "answer": q.answer,
            "keywords": q.keywords, "news_id": q.news_id}


@router.put("/{question_id}")
async def update_question_endpoint(question_id: int, data: QuestionCreate):
    q = await db_update_question(
        question_id=question_id,
        question=data.question,
        answer=data.answer,
        category=None,
        keywords=data.keywords,
        news_id=data.news_id,
    )
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"id": q.id, "question": q.question, "answer": q.answer,
            "keywords": q.keywords, "news_id": q.news_id}


@router.get("/search/{text}")
async def search_questions(text: str):
    result = await search_question(text)
    if result:
        await increment_question_usage(result.id)
        return {"question": result.question, "answer": result.answer, "news_id": result.news_id}
    return {"message": "لم أجد جواب على سؤالك، جرب أسئلة ثانية أو اسأل في القروب"}


@router.delete("/{question_id}")
async def delete_question_endpoint(question_id: int):
    await delete_question(question_id)
    return {"status": "deleted"}
