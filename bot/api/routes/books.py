import httpx
import os
import asyncio
import tempfile
import fitz
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select, func
from bot.models.models import Book, BookGroup, ChannelGroup
from bot.services.database import (
    async_session, add_book, get_all_books, get_books_by_group,
    delete_book, get_all_book_groups, get_book_group_by_id,
    create_book_group, delete_book_group, update_book_group,
    get_active_channel_groups, get_official_channel
)
from bot.services.cloud_storage import upload_raw, upload_raw_streaming
from bot.config import BOT_TOKEN

router = APIRouter()


def _generate_pdf_thumbnail_bytes(pdf_bytes: bytes) -> bytes | None:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        doc = fitz.open(tmp_path)
        if len(doc) > 0:
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            thumb_path = tmp_path.rsplit('.', 1)[0] + '_thumb.jpg'
            pix.save(thumb_path)
            with open(thumb_path, 'rb') as f:
                thumb_bytes = f.read()
            os.unlink(thumb_path)
            doc.close()
            os.unlink(tmp_path)
            try:
                from PIL import Image
                from io import BytesIO
                img = Image.open(BytesIO(thumb_bytes))
                img.thumbnail((320, 320), Image.LANCZOS)
                buf = BytesIO()
                img.save(buf, "JPEG", quality=85)
                return buf.getvalue()
            except Exception:
                return thumb_bytes
        doc.close()
        os.unlink(tmp_path)
    except Exception:
        pass
    return None


async def _get_channel_id():
    official = await get_official_channel()
    if official:
        return official.chat_id
    channels = await get_active_channel_groups()
    for ch in channels:
        if ch.type == 'channel':
            return ch.chat_id
    return None


async def _get_channel_username():
    official = await get_official_channel()
    if official and official.invite_link:
        link = official.invite_link
        if 't.me/' in link:
            return link.split('t.me/')[-1].strip('/')
    if official:
        return str(official.chat_id)

    async with async_session() as session:
        stmt = select(ChannelGroup).where(
            ChannelGroup.type == 'channel',
            ChannelGroup.is_active == True
        ).order_by(ChannelGroup.created_at.desc()).limit(1)
        result = await session.execute(stmt)
        channel = result.scalar_one_or_none()
        if channel and channel.invite_link:
            link = channel.invite_link
            if 't.me/' in link:
                return link.split('t.me/')[-1].strip('/')
        if channel:
            return str(channel.chat_id)
        return None


async def update_book_group_post(group_id: int, force_new: bool = False):
    async with async_session() as session:
        stmt = select(BookGroup).where(BookGroup.id == group_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()

        if not group:
            return

        books_stmt = select(Book).where(
            Book.group_id == group_id,
            Book.is_active == True
        ).order_by(Book.channel_message_id.asc().nullslast())
        books_result = await session.execute(books_stmt)
        all_books = books_result.scalars().all()

        published = [b for b in all_books if b.channel_message_id]

        if not published:
            if group.channel_message_id:
                channel_chat_id = await _get_channel_id()
                async with httpx.AsyncClient() as client:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": channel_chat_id, "message_id": group.channel_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                group.channel_message_id = None
                await session.commit()
            return

        channel_chat_id = await _get_channel_id()
        channel_username = await _get_channel_username()
        if not channel_username:
            return

        text = f"{group.title}\n"
        for book in published:
            book_link = f"https://t.me/{channel_username}/{book.channel_message_id}"
            text += f"{book.title} 🔻\n{book_link}\n\n"
        text += "#شاركها_فربما_يبحث_عنها_غيرك"

        channel_chat_id = await _get_channel_id()

        async with httpx.AsyncClient() as client:
            if group.channel_message_id and not force_new:
                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
                    data={
                        "chat_id": channel_chat_id,
                        "message_id": group.channel_message_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    },
                    timeout=30
                )
            else:
                if force_new and group.channel_message_id:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": channel_chat_id, "message_id": group.channel_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                    group.channel_message_id = None
                    await session.commit()

                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    data={
                        "chat_id": channel_chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    },
                    timeout=30
                )
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get("ok"):
                        group.channel_message_id = result["result"]["message_id"]
                        await session.commit()


class BookGroupCreate(BaseModel):
    title: str
    description: Optional[str] = None
    group_tag: Optional[str] = None


class BookCreate(BaseModel):
    title: str
    file_url: Optional[str] = None
    group_id: Optional[int] = None
    author: Optional[str] = None
    link: Optional[str] = None


# ==================== Book Groups ====================
@router.get("/groups")
async def get_book_groups():
    return await get_all_book_groups()


@router.get("/groups/{group_id}")
async def get_book_group(group_id: int):
    group = await get_book_group_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    books = await get_books_by_group(group_id)
    return {"group": group, "books": books}


@router.post("/groups")
async def create_book_group_endpoint(data: BookGroupCreate):
    group = await create_book_group(title=data.title, description=data.description, group_tag=data.group_tag)
    return {"id": group.id, "title": group.title, "group_tag": group.group_tag, "message": "تم حفظ المجموعة كمسودة"}


@router.put("/groups/{group_id}")
async def update_book_group_endpoint(group_id: int, data: BookGroupCreate):
    async with async_session() as session:
        stmt = select(BookGroup).where(BookGroup.id == group_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        if data.title is not None:
            group.title = data.title
        if data.description is not None:
            group.description = data.description
        if data.group_tag is not None:
            group.group_tag = data.group_tag
        await session.commit()

    await update_book_group_post(group_id)
    return {"id": group_id, "title": data.title, "group_tag": data.group_tag, "message": "Group updated successfully"}


@router.delete("/groups/{group_id}")
async def delete_book_group_endpoint(group_id: int, mode: str = "permanent"):
    if mode == "reset":
        async with async_session() as session:
            stmt = select(BookGroup).where(BookGroup.id == group_id)
            result = await session.execute(stmt)
            group = result.scalar_one_or_none()
            if not group:
                return {"error": "المجموعة غير موجودة"}

            books_stmt = select(Book).where(Book.group_id == group_id)
            books_result = await session.execute(books_stmt)
            all_books = books_result.scalars().all()

            channel_chat_id = await _get_channel_id()

            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                if group.channel_message_id:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": channel_chat_id, "message_id": group.channel_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                    group.channel_message_id = None

                for book in all_books:
                    if book.channel_message_id:
                        try:
                            await client.post(
                                f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                                data={"chat_id": channel_chat_id, "message_id": book.channel_message_id},
                                timeout=30
                            )
                        except Exception:
                            pass
                        book.channel_message_id = None

            await session.commit()
            return {"message": "تم حذف جميع المنشورات من القناة وإعادة تعيين المجموعة", "mode": "reset"}
    else:
        await delete_book_group(group_id)
        return {"status": "deleted", "mode": "permanent"}


# ==================== Books ====================
@router.get("")
async def get_books(
    group_id: Optional[int] = None,
    author: Optional[str] = None,
    search: str = Query(None),
):
    async with async_session() as db:
        base_filter = [Book.is_active == True]
        if group_id:
            base_filter.append(Book.group_id == group_id)
        if author:
            base_filter.append(Book.author == author)
        if search:
            base_filter.append(
                Book.title.ilike(f"%{search}%") | Book.author.ilike(f"%{search}%")
            )

        result = await db.execute(
            select(Book).where(*base_filter)
        )
        items = result.scalars().all()
    return {
        "items": [
            {
                "id": b.id,
                "title": b.title,
                "description": b.description,
                "author": b.author,
                "file_url": b.file_url,
                "group_id": b.group_id,
                "link": b.link,
                "channel_message_id": b.channel_message_id,
                "is_active": b.is_active,
            }
            for b in items
        ],
        "total": len(items),
    }


@router.post("")
async def create_book(data: BookCreate):
    return await add_book(title=data.title,
                         file_url=data.file_url, group_id=data.group_id,
                         author=data.author, link=data.link)


@router.post("/upload")
async def upload_book(
    title: str = Form(...),
    group_id: int = Form(None),
    author: str = Form(None),
    link: str = Form(None),
    file: Optional[UploadFile] = File(None),
    cloud_files: str = Form("[]"),
):
    file_url = None
    if file:
        try:
            cloud_files_list = __import__('json').loads(cloud_files) if cloud_files else []
        except Exception:
            cloud_files_list = []
        cloud_urls = {cf['index']: cf['url'] for cf in cloud_files_list}

        if 0 in cloud_urls:
            import httpx
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(cloud_urls[0])
                file_data = resp.content
            file_url = upload_raw(file_data, filename=file.filename, folder="kku-bot/books")
        else:
            file_url = upload_raw_streaming(
                file.file,
                filename=file.filename,
                folder="kku-bot/books",
                content_type=file.content_type
            )

    book = await add_book(
        title=title,
        file_url=file_url,
        group_id=group_id,
        author=author,
        link=link,
    )

    return {
        "id": book.id,
        "title": book.title,
        "description": book.description,
        "author": book.author,
        "file_url": book.file_url,
        "group_id": book.group_id,
        "link": book.link,
        "channel_message_id": book.channel_message_id,
        "is_active": book.is_active,
        "message": "تم حفظ الكتاب كمسودة",
    }


@router.post("/publish-book/{book_id}")
async def publish_single_book(book_id: int):
    async with async_session() as session:
        stmt = select(Book).where(Book.id == book_id)
        result = await session.execute(stmt)
        book = result.scalar_one_or_none()

        if not book:
            return {"error": "الكتاب غير موجود"}
        if not book.file_url:
            return {"error": "الكتاب لا يحتوي على ملف مرفوع"}

        group = None
        if book.group_id:
            g_stmt = select(BookGroup).where(BookGroup.id == book.group_id)
            g_result = await session.execute(g_stmt)
            group = g_result.scalar_one_or_none()

        import asyncio
        from bot.services.cloud_storage import download_raw

        channel_chat_id = await _get_channel_id()

        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            file_content = None
            for dl_attempt in range(3):
                try:
                    file_resp = await client.get(book.file_url, timeout=90)
                    if file_resp.status_code == 200:
                        file_content = file_resp.content
                        break
                except Exception as e:
                    print(f"Download attempt {dl_attempt+1} failed: {e}")
                if dl_attempt < 2:
                    await asyncio.sleep(2)

            if not file_content:
                file_content = await asyncio.to_thread(download_raw, book.file_url)

            if not file_content:
                return {"error": "فشل تحميل الملف"}

            caption = ""
            if group and group.group_tag:
                caption += f"#{group.group_tag}\n"
            if book.author:
                caption += f"المؤلف - {book.author}\n\n"
            link = book.link if book.link else "t.me/kkunewbot"
            caption += f'<blockquote>{link}</blockquote>'

            thumb_bytes = _generate_pdf_thumbnail_bytes(file_content)
            send_data = {
                "chat_id": channel_chat_id,
                "caption": caption,
                "parse_mode": "HTML"
            }
            files_dict = {"document": (f"{book.title}{os.path.splitext(book.file_url)[1] or '.pdf'}", file_content, "application/pdf")}
            if thumb_bytes:
                files_dict["thumbnail"] = ("thumb.jpg", thumb_bytes, "image/jpeg")

            resp = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data=send_data,
                files=files_dict,
                timeout=120
            )

            if resp.status_code == 200 and resp.json().get("ok"):
                old_message_id = book.channel_message_id
                if old_message_id:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": channel_chat_id, "message_id": old_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                book.channel_message_id = resp.json()["result"]["message_id"]
                await session.commit()

                if group:
                    await update_book_group_post(group.id, force_new=True)

                return {"message": f"تم نشر {book.title} بنجاح", "book_id": book.id}
            else:
                return {"error": f"فشل النشر: {resp.text}"}


@router.put("/{book_id}")
async def update_book(
    book_id: int,
    title: str = Form(None),
    group_id: int = Form(None),
    author: str = Form(None),
    link: str = Form(None),
    file: UploadFile = File(None),
    cloud_files: str = Form("[]"),
):
    async with async_session() as session:
        stmt = select(Book).where(Book.id == book_id)
        result = await session.execute(stmt)
        book = result.scalar_one_or_none()

        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        old_group_id = book.group_id

        if title is not None:
            book.title = title
        if group_id is not None:
            book.group_id = group_id
        book.author = author if author else None
        book.link = link if link else None

        new_group_id = book.group_id

        if file:
            try:
                cloud_files_list = __import__('json').loads(cloud_files) if cloud_files else []
            except Exception:
                cloud_files_list = []
            cloud_urls = {cf['index']: cf['url'] for cf in cloud_files_list}

            if 0 in cloud_urls:
                import httpx
                async with httpx.AsyncClient(timeout=120) as client:
                    resp = await client.get(cloud_urls[0])
                    file_data = resp.content
                file_url = upload_raw(file_data, filename=file.filename, folder="kku-bot/books")
            else:
                file_url = upload_raw_streaming(
                    file.file,
                    filename=file.filename,
                    folder="kku-bot/books",
                    content_type=file.content_type
                )
            book.file_url = file_url

        await session.commit()

    if old_group_id and old_group_id != new_group_id:
        await update_book_group_post(old_group_id)
    if new_group_id:
        await update_book_group_post(new_group_id)

    return {"message": "Book updated successfully", "id": book_id}


@router.delete("/{book_id}")
async def delete_book_endpoint(book_id: int, mode: str = "permanent"):
    if mode == "reset":
        async with async_session() as session:
            stmt = select(Book).where(Book.id == book_id)
            result = await session.execute(stmt)
            book = result.scalar_one_or_none()
            if not book:
                return {"error": "الكتاب غير موجود"}

            group_id = book.group_id

            if book.channel_message_id:
                channel_chat_id = await _get_channel_id()
                async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                    try:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": channel_chat_id, "message_id": book.channel_message_id},
                            timeout=30
                        )
                    except Exception:
                        pass
                book.channel_message_id = None
                await session.commit()

            if group_id:
                await update_book_group_post(group_id)

            return {"message": "تم حذف الكتاب من القناة", "mode": "reset"}
    else:
        async with async_session() as session:
            stmt = select(Book).where(Book.id == book_id)
            result = await session.execute(stmt)
            book = result.scalar_one_or_none()
            group_id = book.group_id if book else None

            if book and book.channel_message_id:
                channel_chat_id = await _get_channel_id()
                try:
                    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                        await client.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                            data={"chat_id": channel_chat_id, "message_id": book.channel_message_id},
                            timeout=30
                        )
                except Exception:
                    pass

        await delete_book(book_id)

        if group_id:
            await update_book_group_post(group_id)

        return {"status": "deleted", "mode": "permanent"}
