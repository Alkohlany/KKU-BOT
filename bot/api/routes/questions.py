from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import update
from bot.services.database import add_question, get_all_questions, search_question, delete_question, increment_question_usage, async_session
from bot.models.models import Question

router = APIRouter()

class QuestionCreate(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None
    keywords: Optional[str] = None

@router.get("/")
async def get_questions():
    return await get_all_questions()

@router.post("/")
async def create_question(data: QuestionCreate):
    return await add_question(question=data.question, answer=data.answer,
                             category=data.category, keywords=data.keywords)

@router.put("/{question_id}")
async def update_question(question_id: int, data: QuestionCreate):
    async with async_session() as session:
        await session.execute(
            update(Question).where(Question.id == question_id).values(
                question=data.question,
                answer=data.answer,
                category=data.category,
                keywords=data.keywords
            )
        )
        await session.commit()
    return {"status": "updated"}

@router.get("/search/{text}")
async def search_questions(text: str):
    result = await search_question(text)
    if result:
        await increment_question_usage(result.id)
        return {"question": result.question, "answer": result.answer, "category": result.category}
    return {"message": "لم أجد جواب على سؤالك، جرب أسئلة ثانية أو اسأل في القروب"}

@router.delete("/{question_id}")
async def delete_question_endpoint(question_id: int):
    await delete_question(question_id)
    return {"status": "deleted"}
