import shutil
import os

source_dir = r"C:\Users\qqq\Downloads\Telegram Desktop"
dest_dir = r"C:\Users\qqq\Desktop\KKU BOT\kku-bot\uploads"

source_files = set(os.listdir(source_dir))
dest_files = set(os.listdir(dest_dir))

# Find PDFs in source not in dest
missing = source_files - dest_files
pdfs_missing = [f for f in missing if f.endswith('.pdf')]

for filename in pdfs_missing:
    src = os.path.join(source_dir, filename)
    dst = os.path.join(dest_dir, filename)
    shutil.copy2(src, dst)
    print(f"copied: {filename}")

if not pdfs_missing:
    print("No missing PDFs found.")
