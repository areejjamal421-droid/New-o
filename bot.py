import os
import sqlite3
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =========================
# SETTINGS
# =========================

TOKEN = "9109483206:AAG60PTMWYKmkhtHFZJ5OdfShYAm9vD0D30"
ADMIN_ID = 8292471160

DB_NAME = "density78bot.db"

logging.basicConfig(level=logging.INFO)


# =========================
# DATABASE
# =========================

def db():
    return sqlite3.connect(DB_NAME)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lectures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER,
        title TEXT,
        file_id TEXT
    )
    """)

    con.commit()
    con.close()


# =========================
# ADMIN CHECK
# =========================

def is_admin(user_id):
    return user_id == ADMIN_ID


# =========================
# KEYBOARDS
# =========================

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة مادة", callback_data="add_subject")],
        [InlineKeyboardButton("📄 إضافة شيت", callback_data="upload")],
        [InlineKeyboardButton("✏️ تعديل عنوان شيت", callback_data="edit")],
        [InlineKeyboardButton("🗑 حذف شيت", callback_data="delete")],
        [InlineKeyboardButton("❌ حذف مادة", callback_data="delete_subject")],
        [InlineKeyboardButton("📚 عرض المحتوى", callback_data="content")]
    ])


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("📚 تصفح المواد الدراسية", callback_data="subjects")]
    ]

    await update.message.reply_text(
        "أهلاً بك في Density78bot 🎓\n\n"
        "بوت الشيتات والمحاضرات الخاص بطلبة تقنية الأسنان.\n\n"
        "اختاري المادة للبدء:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# ADMIN PANEL
# =========================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("ليس لديك صلاحية الدخول.")
        return

    await update.message.reply_text(
        "⚙️ لوحة تحكم الإدارة\n\nاختاري العملية:",
        reply_markup=admin_keyboard()
    )


# =========================
# SUBJECT LIST
# =========================

async def show_subjects(query):

    con = db()
    cur = con.cursor()

    cur.execute("SELECT id, name FROM subjects")
    subjects = cur.fetchall()

    con.close()

    buttons = [
        [InlineKeyboardButton(name, callback_data=f"subject_{sid}")]
        for sid, name in subjects
    ]

    if not buttons:
        buttons = [
            [InlineKeyboardButton("لا توجد مواد حالياً", callback_data="none")]
        ]

    await query.edit_message_text(
        "📚 اختاري المادة:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# =========================
# CALLBACKS
# =========================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    if data == "none":
        return

    if data == "subjects":
        await show_subjects(query)
        return

    # ADMIN PROTECTION
    admin_actions = [
        "add_subject", "upload", "edit",
        "delete", "delete_subject", "content"
    ]

    if data in admin_actions and not is_admin(user_id):
        await query.answer("غير مسموح لك.", show_alert=True)
        return

    # ADD SUBJECT
    if data == "add_subject":
        context.user_data["action"] = "add_subject"

        await query.edit_message_text(
            "✍️ اكتبي اسم المادة الجديدة:"
        )
        return

    # UPLOAD SHEET
    if data == "upload":

        con = db()
        cur = con.cursor()
        cur.execute("SELECT id, name FROM subjects")
        subjects = cur.fetchall()
        con.close()

        buttons = [
            [InlineKeyboardButton(name, callback_data=f"up_{sid}")]
            for sid, name in subjects
        ]

        if not buttons:
            await query.edit_message_text(
                "لا توجد مواد. أضيفي مادة أولاً."
            )
            return

        await query.edit_message_text(
            "📚 اختاري المادة التي تريدين إضافة الشيت إليها:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # SELECT SUBJECT FOR UPLOAD
    if data.startswith("up_"):

        sid = int(data.split("_")[1])

        context.user_data["action"] = "upload_title"
        context.user_data["subject_id"] = sid

        await query.edit_message_text(
            "✍️ اكتبي عنوان المحاضرة أو الشيت:"
        )
        return

    # EDIT SHEET
    if data == "edit":
        con = db()
        cur = con.cursor()
        cur.execute("SELECT id, title FROM lectures")
        lectures = cur.fetchall()
        con.close()

        buttons = [
            [InlineKeyboardButton(title, callback_data=f"ren_{lid}")]
            for lid, title in lectures
        ]

        if not buttons:
            await query.edit_message_text("لا توجد شيتات.")
            return

        await query.edit_message_text(
            "اختاري الشيت الذي تريدين تعديل عنوانه:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data.startswith("ren_"):
        lid = int(data.split("_")[1])

        context.user_data["action"] = "rename"
        context.user_data["lecture_id"] = lid

        await query.edit_message_text(
            "✍️ اكتبي العنوان الجديد:"
        )
        return

    # DELETE LECTURE
    if data == "delete":

        con = db()
        cur = con.cursor()
        cur.execute("SELECT id, title FROM lectures")
        lectures = cur.fetchall()
        con.close()

        buttons = [
            [InlineKeyboardButton(
                f"🗑 {title}",
                callback_data=f"del_{lid}"
            )]
            for lid, title in lectures
        ]

        if not buttons:
            await query.edit_message_text("لا توجد شيتات للحذف.")
            return

        await query.edit_message_text(
            "اختاري الشيت الذي تريدين حذفه:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data.startswith("del_"):
        if not is_admin(user_id):
            return

        lid = int(data.split("_")[1])

        con = db()
        cur = con.cursor()
        cur.execute("DELETE FROM lectures WHERE id=?", (lid,))
        con.commit()
        con.close()

        await query.edit_message_text("✅ تم حذف الشيت بنجاح.")
        return

    # DELETE SUBJECT
    if data == "delete_subject":

        con = db()
        cur = con.cursor()
        cur.execute("SELECT id, name FROM subjects")
        subjects = cur.fetchall()
        con.close()

        buttons = [
            [InlineKeyboardButton(
                f"❌ {name}",
                callback_data=f"dels_{sid}"
            )]
            for sid, name in subjects
        ]

        if not buttons:
            await query.edit_message_text("لا توجد مواد.")
            return

        await query.edit_message_text(
            "اختاري المادة التي تريدين حذفها:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data.startswith("dels_"):
        sid = int(data.split("_")[1])

        con = db()
        cur = con.cursor()

        cur.execute("DELETE FROM lectures WHERE subject_id=?", (sid,))
        cur.execute("DELETE FROM subjects WHERE id=?", (sid,))

        con.commit()
        con.close()

        await query.edit_message_text(
            "✅ تم حذف المادة والشيتات التابعة لها."
        )
        return

    # SHOW CONTENT
    if data == "content":

        con = db()
        cur = con.cursor()

        cur.execute("""
        SELECT subjects.name, lectures.title
        FROM subjects
        LEFT JOIN lectures ON subjects.id = lectures.subject_id
        ORDER BY subjects.id
        """)

        rows = cur.fetchall()
        con.close()

        if not rows:
            await query.edit_message_text("المكتبة فارغة.")
            return

        text = "📚 محتويات المكتبة:\n\n"

        for subject, title in rows:
            text += f"📖 {subject}\n"
            text += f"   • {title or 'لا توجد شيتات'}\n"

        await query.edit_message_text(text)
        return

    # STUDENT SELECT SUBJECT
    if data.startswith("subject_"):

        sid = int(data.split("_")[1])

        con = db()
        cur = con.cursor()

        cur.execute(
            "SELECT id, title FROM lectures WHERE subject_id=?",
            (sid,)
        )

        lectures = cur.fetchall()
        con.close()

        buttons = [
            [InlineKeyboardButton(
                title,
                callback_data=f"file_{lid}"
            )]
            for lid, title in lectures
        ]

        if not buttons:
            await query.edit_message_text(
                "لا توجد محاضرات مضافة لهذه المادة حالياً."
            )
            return

        await query.edit_message_text(
            "📄 اختاري المحاضرة:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # SEND PDF
    if data.startswith("file_"):

        lid = int(data.split("_")[1])

        con = db()
        cur = con.cursor()

        cur.execute(
            "SELECT title, file_id FROM lectures WHERE id=?",
            (lid,)
        )

        lecture = cur.fetchone()
        con.close()

        if lecture:
            title, file_id = lecture

            await context.bot.send_document(
                chat_id=user_id,
                document=file_id,
                caption=f"📚 {title}"
            )


# =========================
# TEXT MESSAGES
# =========================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if not is_admin(user_id):
        return

    action = context.user_data.get("action")

    if action == "add_subject":

        name = update.message.text.strip()

        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
        con.commit()
        con.close()

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ تمت إضافة المادة: {name}",
            reply_markup=admin_keyboard()
        )

    elif action == "upload_title":

        context.user_data["title"] = update.message.text.strip()
        context.user_data["action"] = "upload_pdf"

        await update.message.reply_text(
            "📄 ممتاز! تو ابعتي ملف PDF للمحاضرة."
        )

    elif action == "rename":

        new_title = update.message.text.strip()
        lid = context.user_data["lecture_id"]

        con = db()
        cur = con.cursor()

        cur.execute(
            "UPDATE lectures SET title=? WHERE id=?",
            (new_title, lid)
        )

        con.commit()
        con.close()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ تم تعديل العنوان بنجاح.",
            reply_markup=admin_keyboard()
        )


# =========================
# PDF UPLOAD
# =========================

async def pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    if context.user_data.get("action") != "upload_pdf":
        return

    document = update.message.document

    if document.mime_type != "application/pdf":
        await update.message.reply_text(
            "❌ الملف لازم يكون PDF."
        )
        return

    sid = context.user_data["subject_id"]
    title = context.user_data["title"]

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO lectures (subject_id, title, file_id)
    VALUES (?, ?, ?)
    """, (sid, title, document.file_id))

    con.commit()
    con.close()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ تمت إضافة الشيت بنجاح!\n"
        f"📚 العنوان: {title}",
        reply_markup=admin_keyboard()
    )


# =========================
# CANCEL
# =========================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    context.user_data.clear()

    await update.message.reply_text(
        "تم إلغاء العملية.",
        reply_markup=admin_keyboard()
    )


# =========================
# MAIN
# =========================

def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing. Add it as an environment variable."
        )

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("cancel", cancel))

    app.add_handler(CallbackQueryHandler(callbacks))

    app.add_handler(
        MessageHandler(filters.Document.PDF, pdf_handler)
    )

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )

    print("Density78bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
