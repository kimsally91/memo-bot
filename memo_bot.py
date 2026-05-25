import os
import psycopg2
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]


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
    await update.message.reply_text(
        "메모봇 시작!\n\n"
        "/memo 내용\n"
        "/search 검색어\n"
        "/list\n"
        "/delete 번호"
    )


async def memo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = " ".join(context.args)

    if not content:
        await update.message.reply_text("메모 내용을 입력해줘.")
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO memos (content, created_at) VALUES (%s, %s) RETURNING id",
        (
            content,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        )
    )

    memo_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    await update.message.reply_text(
        f"저장 완료!\n번호: {memo_id}"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = " ".join(context.args)

    if not keyword:
        await update.message.reply_text("검색어 입력.")
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, content, created_at FROM memos WHERE content ILIKE %s ORDER BY id DESC LIMIT 20",
        (f"%{keyword}%",)
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    if not rows:
        await update.message.reply_text("검색 결과 없음.")
        return

    result = ""

    for row in rows:
        result += f"[{row[0]}] {row[2]}\n{row[1]}\n\n"

    await update.message.reply_text(result)


async def list_memos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, content, created_at FROM memos ORDER BY id DESC LIMIT 20"
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    if not rows:
        await update.message.reply_text("메모 없음.")
        return

    result = ""

    for row in rows:
        result += f"[{row[0]}] {row[2]}\n{row[1]}\n\n"

    await update.message.reply_text(result)


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("번호 입력.")
        return

    memo_id = context.args[0]

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

    if deleted:
        await update.message.reply_text("삭제 완료.")
    else:
        await update.message.reply_text("번호 없음.")


def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("memo", memo))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("list", list_memos))
    app.add_handler(CommandHandler("delete", delete))

    print("메모봇 실행 중")

    app.run_polling()


if __name__ == "__main__":
    main()
