import os
import threading
import psycopg2
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "memo bot running"


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS memos (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
메모봇 시작!

사용법:

메모 내용
검색 키워드
목록
삭제 번호

예시:
메모 오늘 닭상태 좋았음
검색 닭
"""

    await update.message.reply_text(text)


async def save_memo(content):
    conn = get_connection()
    cur = conn.cursor()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    cur.execute(
        "INSERT INTO memos (content, created_at) VALUES (%s, %s) RETURNING id",
        (content, created_at)
    )

    memo_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return memo_id


async def search_memos(keyword):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, content, created_at FROM memos WHERE content ILIKE %s ORDER BY id DESC LIMIT 20",
        (f"%{keyword}%",)
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


async def get_list():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, content, created_at FROM memos ORDER BY id DESC LIMIT 20"
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


async def delete_memo(memo_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM memos WHERE id = %s",
        (memo_id,)
    )

    conn.commit()

    deleted = cur.rowcount

    cur.close()
    conn.close()

    return deleted


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.startswith("메모 "):
        content = text[3:].strip()

        if not content:
            await update.message.reply_text("메모 내용을 입력해줘.")
            return

        memo_id = await save_memo(content)

        await update.message.reply_text(
            f"저장 완료!\n번호: {memo_id}"
        )

    elif text.startswith("검색 "):
        keyword = text[3:].strip()

        if not keyword:
            await update.message.reply_text("검색어 입력.")
            return

        rows = await search_memos(keyword)

        if not rows:
            await update.message.reply_text("검색 결과 없음.")
            return

        result = ""

        for row in rows:
            result += f"[{row[0]}] {row[2]}\n{row[1]}\n\n"

        await update.message.reply_text(result)

    elif text == "목록":
        rows = await get_list()

        if not rows:
            await update.message.reply_text("메모 없음.")
            return

        result = ""

        for row in rows:
            result += f"[{row[0]}] {row[2]}\n{row[1]}\n\n"

        await update.message.reply_text(result)

    elif text.startswith("삭제 "):
        memo_id = text[3:].strip()

        deleted = await delete_memo(memo_id)

        if deleted:
            await update.message.reply_text("삭제 완료.")
        else:
            await update.message.reply_text("번호 없음.")

    else:
        await update.message.reply_text(
            "사용법:\n\n"
            "메모 내용\n"
            "검색 키워드\n"
            "목록\n"
            "삭제 번호"
        )


def start_web_server():
    port = int(os.environ.get("PORT", 10000))

    web_app.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False
    )


def main():
    threading.Thread(
        target=start_web_server,
        daemon=True
    ).start()

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("메모봇 실행 중")

    app.run_polling()


if __name__ == "__main__":
    main()
