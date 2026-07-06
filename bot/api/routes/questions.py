from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import update
from sqlalchemy import select
from bot.services.database import add_question, get_all_questions, search_question, delete_question, increment_question_usage, async_session, update_question as db_update_question
from bot.models.models import Question
from bot.services.cloud_storage import upload_raw

router = APIRouter()

class QuestionCreate(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None
    keywords: Optional[str] = None
    file_url: Optional[str] = None
    file_type: Optional[str] = None


def detect_file_type(filename: str) -> str:
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return 'photo'
    if ext in ('mp4', 'avi', 'mov', 'mkv'):
        return 'video'
    return 'document'


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
        }
        for q in items
    ]


@router.post("/")
async def create_question(data: QuestionCreate):
    q = await add_question(question=data.question, answer=data.answer,
                           category=data.category, keywords=data.keywords,
                           file_url=data.file_url, file_type=data.file_type)
    return {"id": q.id, "question": q.question, "answer": q.answer,
            "category": q.category, "keywords": q.keywords,
            "file_url": q.file_url, "file_type": q.file_type}


@router.post("/upload")
async def create_question_with_file(
    question: str = Form(...),
    answer: str = Form(...),
    category: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    file_url = None
    file_type = None
    if file:
        content = await file.read()
        file_url = upload_raw(content, filename=file.filename, folder="kku-bot/questions")
        file_type = detect_file_type(file.filename)

    q = await add_question(question=question, answer=answer, category=category, keywords=keywords,
                           file_url=file_url, file_type=file_type)
    return {"id": q.id, "question": q.question, "answer": q.answer,
            "category": q.category, "keywords": q.keywords,
            "file_url": q.file_url, "file_type": q.file_type}


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
    )
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"id": q.id, "question": q.question, "answer": q.answer,
            "category": q.category, "keywords": q.keywords,
            "file_url": q.file_url, "file_type": q.file_type}


@router.put("/upload/{question_id}")
async def update_question_with_file(
    question_id: int,
    question: str = Form(None),
    answer: str = Form(None),
    category: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    async with async_session() as session:
        stmt = select(Question).where(Question.id == question_id)
        result = await session.execute(stmt)
        q = result.scalar_one_or_none()
        if not q:
            raise HTTPException(status_code=404, detail="Question not found")
        if question is not None:
            q.question = question
        if answer is not None:
            q.answer = answer
        if category is not None:
            q.category = category
        if keywords is not None:
            q.keywords = keywords
        if file:
            content = await file.read()
            q.file_url = upload_raw(content, filename=file.filename, folder="kku-bot/questions")
            q.file_type = detect_file_type(file.filename)
        await session.commit()
        return {"id": q.id, "question": q.question, "answer": q.answer,
                "category": q.category, "keywords": q.keywords,
                "file_url": q.file_url, "file_type": q.file_type}


@router.get("/search/{text}")
async def search_questions(text: str):
    result = await search_question(text)
    if result:
        await increment_question_usage(result.id)
        return {"question": result.question, "answer": result.answer, "category": result.category, "file_url": result.file_url, "file_type": result.file_type}
    return {"message": "لم أجد جواب على سؤالك، جرب أسئلة ثانية أو اسأل في القروب"}


@router.delete("/{question_id}")
async def delete_question_endpoint(question_id: int):
    await delete_question(question_id)
    return {"status": "deleted"}
