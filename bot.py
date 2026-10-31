import os
import telebot
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "9109483206:AAG60PTMWYKmkhtHFZJ5OdfShYAm9vD0D30"
ADMIN_ID = 123456789  # استبدل هذا الرقم بمعرف الآيدي الخاص بك

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

subjects_data = {
    "ماتيريال": [
        "شيت ماتيريال 1: https://t.example.com/material1.pdf"
    ],
    "اناتومي": [
        "شيت أناتومي 1: https://t.example.com/anatomy1.pdf"
    ]
}

@app.route('/')
def home():
    return "Medical Bot is active!"

@app.route(f'/{TOKEN}', methods=['POST'])
def receive_message():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    for subject in subjects_data.keys():
        markup.add(InlineKeyboardButton(text=subject, callback_data=f"sub_{subject}"))
    
    bot.send_message(
        message.chat.id, 
        "أهلاً بك يَ دكتور 🩶\nاختر المادة لعرض جميع الشيتات الخاصة بها:", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('sub_'))
def callback_inline(call):
    subject_name = call.data.replace('sub_', '')
    if subject_name in subjects_data:
        sheets_list = subjects_data[subject_name]
        response_text = f"📚 **شيتات مادة ({subject_name}):**\n\n" + "\n".join(sheets_list)
        bot.answer_callback_query(call.id, f"تم جلب شيتات {subject_name}")
        bot.send_message(call.message.chat.id, response_text)
    else:
        bot.answer_callback_query(call.id, "عذراً، المادة غير متوفرة حالياً.")

@bot.message_handler(commands=['add'])
def add_sheet(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "عذراً، هذا الأمر مخصص للمشرف فقط ⛔")
        return
    try:
        text_content = message.text.replace('/add', '').strip()
        parts = text_content.split('|')
        subject = parts[0].strip()
        sheet_info = parts[1].strip()
        if subject not in subjects_data:
            subjects_data[subject] = []
        subjects_data[subject].append(sheet_info)
        bot.reply_to(message, f"✅ تم إضافة الشيت بنجاح لمادة ({subject})!")
    except Exception:
        bot.reply_to(message, "⚠️ استخدم الصيغة هكذا:\n`/add الماتيريال | شيت 3: الرابط`", parse_mode="Markdown")

@bot.message_handler(commands=['delete'])
def delete_subject(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "عذراً، هذا الأمر مخصص للمشرف فقط ⛔")
        return
    try:
        subject = message.text.replace('/delete', '').strip()
        if subject in subjects_data:
            del subjects_data[subject]
            bot.reply_to(message, f"🗑️ تم حذف مادة ({subject}) بنجاح!")
        else:
            bot.reply_to(message, "❌ المادة غير موجودة.")
    except Exception:
        bot.reply_to(message, "⚠️ استخدم الصيغة هكذا:\n`/delete الماتيريال`", parse_mode="Markdown")

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f'https://اسم-خدمتك.onrender.com/{TOKEN}')
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
