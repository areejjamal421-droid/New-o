import os
import sqlite3
import logging
from pathlib import Path

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------- Configuration ----------------
BOT_TOKEN = os.getenv("9109483206:AAG60PTMWYKmkhtHFZJ5OdfShYAm9vD0D30", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "8292471160"))
DB_PATH = os.getenv("DB_PATH", "density78bot.db")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ---------------- Database ----------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sheets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE CASCADE
            )
        """)

def get_materials():
    with db() as conn:
        return conn.execute("SELECT id, name FROM materials ORDER BY name").fetchall()

def get_material(material_id):
    with db() as conn:
        return conn.execute(
            "SELECT id, name FROM materials WHERE id = ?", (material_id,)
        ).fetchone()

def get_sheets(material_id):
    with db() as conn:
        return conn.execute(
            "SELECT id, file_id, file_name FROM sheets WHERE material_id = ? ORDER BY id",
            (material_id,),
        ).fetchall()

def add_material(name):
    with db() as conn:
        conn.execute("INSERT INTO materials(name) VALUES(?)", (name,))

def rename_material(material_id, name):
    with db() as conn:
        conn.execute(
            "UPDATE materials SET name = ? WHERE id = ?", (name, material_id)
        )

def delete_material(material_id):
    with db() as conn:
        conn.execute("DELETE FROM sheets WHERE material_id = ?", (material_id,))
        conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))

def add_sheet(material_id, file_id, file_name):
    with db() as conn:
        conn.execute(
            "INSERT INTO sheets(material_id, file_id, file_name) VALUES(?, ?, ?)",
            (material_id, file_id, file_name),
        )

def delete_sheet(sheet_id):
    with db() as conn:
        conn.execute("DELETE FROM sheets WHERE id = ?", (sheet_id,))

# ---------------- Keyboards ----------------
ADMIN_HOME = [
    ["➕ إضافة مادة", "✏️ تعديل مادة"],
    ["🗑️ حذف مادة", "➕ إضافة شيت"],
    ["🗑️ حذف شيت", "📚 عرض المواد"],
    ["🏠 قائمة الطلبة"],
]
STUDENT_HOME = [["ℹ️ طريقة الاستخدام"]]

def home_keyboard(is_admin=False):
    rows = [list(row) for row in STUDENT_HOME]
    materials = get_materials()
    # Put material buttons in rows of two, at the bottom of the chat.
    for i in range(0, len(materials), 2):
        rows.append([m["name"] for m in materials[i:i+2]])
    if is_admin:
        rows.append(["👑 لوحة الأدمن"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def admin_keyboard():
    return ReplyKeyboardMarkup(ADMIN_HOME, resize_keyboard=True)

def choose_material_keyboard():
    rows = [[m["name"]] for m in get_materials()]
    rows.append(["❌ إلغاء"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def is_admin(update: Update):
    return bool(update.effective_user and update.effective_user.id == ADMIN_ID)

async def say(update: Update, text, keyboard=None):
    await update.effective_message.reply_text(
        text, reply_markup=keyboard or home_keyboard(is_admin(update))
    )

# ---------------- Commands ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await say(
        update,
        "أهلاً بك في بوت الشيتات 📚\nاختار المادة من الأزرار الموجودة تحت.",
        home_keyboard(is_admin(update)),
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await say(update, "تم إلغاء العملية.", home_keyboard(is_admin(update)))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    mode = context.user_data.get("mode")

    if text == "❌ إلغاء":
        await cancel(update, context)
        return

    # Admin-only workflows
    if text == "👑 لوحة الأدمن":
        if not is_admin(update):
            await say(update, "غير مسموح لك باستخدام لوحة الأدمن.")
            return
        context.user_data.clear()
        await say(update, "لوحة تحكم الأدمن 👑\nاختاري العملية:", admin_keyboard())
        return

    if text == "🏠 قائمة الطلبة":
        context.user_data.clear()
        await say(update, "قائمة المواد:", home_keyboard(is_admin(update)))
        return

    if text == "ℹ️ طريقة الاستخدام":
        await say(
            update,
            "اختار المادة من الأزرار بالأسفل، وبعدها اضغط على اسم الشيت لإرساله.",
        )
        return

    if is_admin(update):
        if text == "➕ إضافة مادة":
            context.user_data.clear()
            context.user_data["mode"] = "add_material"
            await say(update, "اكتبي اسم المادة الجديدة:", ReplyKeyboardRemove())
            return

        if text == "✏️ تعديل مادة":
            if not get_materials():
                await say(update, "مافيش مواد لتعديلها.", admin_keyboard())
                return
            context.user_data.clear()
            context.user_data["mode"] = "rename_choose"
            await say(update, "اختاري المادة اللي تبي تعدلي اسمها:", choose_material_keyboard())
            return

        if text == "🗑️ حذف مادة":
            if not get_materials():
                await say(update, "مافيش مواد لحذفها.", admin_keyboard())
                return
            context.user_data.clear()
            context.user_data["mode"] = "delete_material"
            await say(update, "اختاري المادة. تنبيه: حذف المادة يحذف شيتاتها معها:", choose_material_keyboard())
            return

        if text == "➕ إضافة شيت":
            if not get_materials():
                await say(update, "أضيفي مادة أولاً، وبعدها تقدري تضيفي شيتاتها.", admin_keyboard())
                return
            context.user_data.clear()
            context.user_data["mode"] = "add_sheet_choose"
            await say(update, "اختاري المادة اللي تبي تضيفيلها شيت:", choose_material_keyboard())
            return

        if text == "🗑️ حذف شيت":
            if not get_materials():
                await say(update, "مافيش مواد حالياً.", admin_keyboard())
                return
            context.user_data.clear()
            context.user_data["mode"] = "delete_sheet_choose"
            await say(update, "اختاري المادة:", choose_material_keyboard())
            return

        if text == "📚 عرض المواد":
            materials = get_materials()
            if not materials:
                msg = "مافيش مواد مضافة حالياً."
            else:
                lines = []
                for m in materials:
                    lines.append(f"• {m['name']} — {len(get_sheets(m['id']))} شيت")
                msg = "المواد الموجودة:\n" + "\n".join(lines)
            await say(update, msg, admin_keyboard())
            return

    # Workflow state handling
    if mode == "add_material":
        name = text.strip()
        if not name or len(name) > 60:
            await say(update, "اسم المادة لازم يكون من 1 إلى 60 حرف. حاولي مرة ثانية:")
            return
        try:
            add_material(name)
            context.user_data.clear()
            await say(update, f"تمت إضافة مادة «{name}» بنجاح ✅", admin_keyboard())
        except sqlite3.IntegrityError:
            await say(update, "المادة موجودة بالفعل. اكتبي اسماً مختلفاً:")
        return

    if mode in ("rename_choose", "delete_material", "add_sheet_choose", "delete_sheet_choose"):
        material = next((m for m in get_materials() if m["name"] == text), None)
        if not material:
            await say(update, "اختاري مادة من الأزرار الظاهرة تحت.")
            return

        if mode == "rename_choose":
            context.user_data["mode"] = "rename_material"
            context.user_data["material_id"] = material["id"]
            await say(update, f"اكتبي الاسم الجديد لمادة «{material['name']}»:", ReplyKeyboardRemove())
            return

        if mode == "delete_material":
            delete_material(material["id"])
            context.user_data.clear()
            await say(update, f"تم حذف مادة «{material['name']}» وكل شيتاتها.", admin_keyboard())
            return

        if mode == "add_sheet_choose":
            context.user_data["mode"] = "add_sheet_upload"
            context.user_data["material_id"] = material["id"]
            await say(
                update,
                f"تمام. ابعتي ملف الشيت الآن لمادة «{material['name']}» كملف PDF أو مستند.",
                ReplyKeyboardRemove(),
            )
            return

        if mode == "delete_sheet_choose":
            sheets = get_sheets(material["id"])
            if not sheets:
                context.user_data.clear()
                await say(update, f"مافيش شيتات في مادة «{material['name']}».", admin_keyboard())
                return
            context.user_data["mode"] = "delete_sheet_select"
            context.user_data["material_id"] = material["id"]
            context.user_data["sheet_ids"] = [s["id"] for s in sheets]
            lines = [f"{i+1}. {s['file_name']}" for i, s in enumerate(sheets)]
            await say(update, "ابعتي رقم الشيت اللي تبي تحذفيه:\n\n" + "\n".join(lines), ReplyKeyboardRemove())
            return

    if mode == "rename_material":
        name = text.strip()
        if not name or len(name) > 60:
            await say(update, "اكتبي اسماً من 1 إلى 60 حرف:")
            return
        try:
            rename_material(context.user_data["material_id"], name)
            context.user_data.clear()
            await say(update, f"تم تعديل اسم المادة إلى «{name}» ✅", admin_keyboard())
        except sqlite3.IntegrityError:
            await say(update, "فيه مادة ثانية بنفس الاسم. اكتبي اسماً مختلفاً:")
        return

    if mode == "delete_sheet_select":
        try:
            index = int(text) - 1
            ids = context.user_data["sheet_ids"]
            if index < 0 or index >= len(ids):
                raise ValueError
            delete_sheet(ids[index])
            context.user_data.clear()
            await say(update, "تم حذف الشيت بنجاح 🗑️", admin_keyboard())
        except ValueError:
            await say(update, "ابعتي رقم صحيح من القائمة.")
        return

    # Material selection for students
    material = next((m for m in get_materials() if m["name"] == text), None)
    if material:
        sheets = get_sheets(material["id"])
        if not sheets:
            await say(update, f"مادة «{material['name']}» مازال ما فيهاش شيتات.")
            return
        await update.message.reply_text(
            f"📚 شيتات مادة {material['name']} — العدد: {len(sheets)}"
        )
        for sheet in sheets:
            try:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=sheet["file_id"],
                    caption=sheet["file_name"],
                )
            except Exception:
                log.exception("Failed sending sheet %s", sheet["id"])
                await update.message.reply_text(
                    f"تعذر إرسال الملف: {sheet['file_name']}."
                )
        return

    await say(update, "مش فاهم طلبك. اختار مادة من الأزرار الموجودة تحت.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await say(update, "إضافة الشيتات متاحة للأدمن فقط.")
        return
    if context.user_data.get("mode") != "add_sheet_upload":
        await say(update, "افتحي لوحة الأدمن واختاري «إضافة شيت» أولاً.")
        return
    document = update.message.document
    if not document:
        await say(update, "ابعتي الملف كمستند، ويفضل PDF.")
        return
    material_id = context.user_data.get("material_id")
    material = get_material(material_id)
    if not material:
        context.user_data.clear()
        await say(update, "المادة لم تعد موجودة. ابدئي العملية من جديد.", admin_keyboard())
        return
    file_name = document.file_name or "Study sheet"
    add_sheet(material_id, document.file_id, file_name)
    context.user_data.clear()
    await say(
        update,
        f"تم حفظ «{file_name}» ضمن مادة «{material['name']}» بنجاح ✅",
        admin_keyboard(),
    )

async def handle_non_document_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update) and context.user_data.get("mode") == "add_sheet_upload":
        await say(update, "ابعتي الشيت كملف PDF أو مستند، مش كصورة عادية.")
    else:
        await say(update, "اختار مادة من الأزرار الموجودة تحت.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Unhandled error", exc_info=context.error)

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Add it as an environment variable.")
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.ALL & ~filters.Document.ALL & ~filters.TEXT, handle_non_document_file))
    app.add_error_handler(error_handler)
    log.info("Density78bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
