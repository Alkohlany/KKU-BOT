from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from bot.services.database import add_question, get_all_questions, search_question, delete_question, increment_question_usage, update_question as db_update_question

router = APIRouter()

class QuestionCreate(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None
    keywords: Optional[str] = None
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    as_document: bool = False


@router.get("/")
async def get_questions():
    items = await get_all_questions()
    return [
        {
            "id": q.id,
            "question": q.question,
            "answer": q.answer,
            "category": q.category,
            "keywords": q.keywords,
            "file_url": q.file_url,
            "file_type": q.file_type,
            "as_document": q.as_document,
        }
        for q in items
    ]


@router.post("/")
async def create_question(data: QuestionCreate):
    q = await add_question(question=data.question, answer=data.answer,
                           category=data.category, keywords=data.keywords,
                           file_url=data.file_url, file_type=data.file_type,
                           as_document=data.as_document)
    return {"id": q.id, "question": q.question, "answer": q.answer,
            "category": q.category, "keywords": q.keywords,
            "file_url": q.file_url, "file_type": q.file_type,
            "as_document": q.as_document}


@router.put("/{question_id}")
async def update_question_endpoint(question_id: int, data: QuestionCreate):
    q = await db_update_question(
        question_id=question_id,
        question=data.question,
        answer=data.answer,
        category=data.category,
        keywords=data.keywords,
        file_url=data.file_url,
        file_type=data.file_type,
        as_document=data.as_document,
    )
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"id": q.id, "question": q.question, "answer": q.answer,
            "category": q.category, "keywords": q.keywords,
            "file_url": q.file_url, "file_type": q.file_type,
            "as_document": q.as_document}


@router.get("/search/{text}")
async def search_questions(text: str):
    result = await search_question(text)
    if result:
        await increment_question_usage(result.id)
        return {"question": result.question, "answer": result.answer, "category": result.category, "file_url": result.file_url, "file_type": result.file_type, "as_document": result.as_document}
    return {"message": "لم أجد جواب على سؤالك، جرب أسئلة ثانية أو اسأل في القروب"}


@router.delete("/{question_id}")
async def delete_question_endpoint(question_id: int):
    await delete_question(question_id)
    return {"status": "deleted"}
