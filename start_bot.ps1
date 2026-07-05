Start-Process -FilePath "py" -ArgumentList "-m","bot.main" -WorkingDirectory "C:\Users\qqq\Desktop\KKU BOT\kku-bot" -WindowStyle Minimized
Start-Process -FilePath "py" -ArgumentList "-m","uvicorn","bot.api.main:app","--host","0.0.0.0","--port","8000" -WorkingDirectory "C:\Users\qqq\Desktop\KKU BOT\kku-bot" -WindowStyle Minimized
