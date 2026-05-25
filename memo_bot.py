import os
import psycopg2
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_conn()
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
/memo 내용 → 메모 저장
/search 검색어 → 메모 검색
/list → 최근 메모 보기
/delete 번호 → 메모 삭제

예시:
/memo 오늘 닭값 체크
/search 닭값
"""

    await update.message.reply_text(text)


async def memo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = " ".join(context.args)

    if not content:
        await update.message.reply_text("메모 내용을 적어줘.")
        return

    conn = get_conn()
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

    await update.message.reply_text(
        f"저장 완료!\n번호: {memo_id}\n내용: {content}"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = " ".join(context.args)

    if not keyword:
        await update.message.reply_text("검색어를 입력해줘.")
        return

    conn = get_conn()
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

    result = f"검색 결과: {keyword}\n\n"

    for row in rows:
        result += f"[{row[0]}] {row[2]}\n{row[1]}\n\n"

    await update.message.reply_text(result)


async def list_memos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_conn()
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

    result = "최근 메모\n\n"

    for row in rows:
        result += f"[{row[0]}] {row[2]}\n{row[1]}\n\n"

    await update.message.reply_text(result)


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("삭제할 번호 입력.")
        return

    memo_id = context.args[0]

    conn = get_conn()
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
        await update.message.reply_text(f"{memo_id}번 삭제 완료.")
    else:
        await update.message.reply_text("해당 번호 없음.")


def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("memo", memo))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("list", list_memos))
    app.add_handler(CommandHandler("delete", delete))

    print("메모봇 실행 중...")

    app.run_polling()


if __name__ == "__main__":
    main()


