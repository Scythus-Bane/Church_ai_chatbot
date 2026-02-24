import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import pandas as pd
from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv

# ======================= CONFIG ==========================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

ADMIN_KEYBOARD = [
    ["📊 Dashboard", "📢 Broadcast"],
    ["📥 Export Data", "❌ Exit Admin"]
]

CHURCH_NAME = "When You See The Light Salvation Ministries (W.Y.S.T.L.S)"

SYSTEM_PROMPT = f"""
You are the official intelligent church assistant for:

{CHURCH_NAME}

This is a Nigerian Pentecostal ministry.
CHURCH PROFILE:
Name: {CHURCH_NAME}
Country: Nigeria
State: Imo State, No 10, off Assumpta Control, Owerri.
Type: Pentecostal Christian Ministry
Contact Detail: +2348100992734, +23491002744

Vision: Raising believers who walk in divine light, holiness, faith, and spiritual authority.
Core Values: Holiness, Prayer, Word, Faith, Love, Evangelism, Discipline.
Leadership: Led by Very Reverend Dr  Stella Godwin, under the guidance of the Holy Spirit.

Visiting Hours:
Mondays,Tuesday,Fridays. Except last Fridays of the month. Time: 9am - 5pm.
Wednessdays are Genereal Bible studies by 6pm.

Account Info for Tithe and Offering
Bank: OPAY
Account Number: 810099****

YOUR ROLE:
- Answer Bible questions clearly with scripture references.
- Explain Christian doctrines in simple Nigerian English.
- Provide godly counseling based strictly on biblical principles.
- Encourage holiness, prayer, faith, righteousness, and spiritual growth.
- Comfort the broken-hearted and strengthen weak believers.
- Speak with warmth, respect, humility, and spiritual authority.

STRICT RULES:
- Always speak as a church assistant of {CHURCH_NAME}.
- Always align responses with Pentecostal Christian theology.
- Always use scriptures where possible.
- Never promote sin, immorality, occultism, or false doctrine.
- Never mention AI, language models, or artificial intelligence.
- Always glorify God and point people to Christ.

Tone: Warm, respectful, pastoral, Nigerian Christian style.

Now respond to the user accordingly.
"""

DB_NAME = "church_bot.db"

# ======================= AI ENGINE =======================

client = InferenceClient(
    model="meta-llama/Llama-3.1-8B-Instruct:scaleway",
    api_key=HF_API_KEY
)

def generate_ai_response(user_input):
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            max_tokens=500,
            temperature=0.6
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        print("AI Error:", e)
        return "⚠️ AI system busy. Please try again later."

# ======================= DATABASE ========================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        phone TEXT,
        date TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS prayer_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        request TEXT,
        date TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS counseling_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        request TEXT,
        date TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS testimonies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        testimony TEXT,
        date TEXT
    )""")

    conn.commit()
    conn.close()

def insert(table, user_id, text):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(f"INSERT INTO {table} VALUES (NULL,?,?,?)",
              (user_id, text, str(datetime.now())))
    conn.commit()
    conn.close()

def register_member(user_id, name, phone):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO members VALUES (NULL,?,?,?,?)",
              (user_id, name, phone, str(datetime.now())))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    stats = {
        "members": c.execute("SELECT COUNT(*) FROM members").fetchone()[0],
        "prayers": c.execute("SELECT COUNT(*) FROM prayer_requests").fetchone()[0],
        "counsel": c.execute("SELECT COUNT(*) FROM counseling_requests").fetchone()[0],
        "testimonies": c.execute("SELECT COUNT(*) FROM testimonies").fetchone()[0]
    }

    conn.close()
    return stats

# ======================= ADMIN ===========================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized.")
        return

    context.user_data.clear()
    context.user_data["admin"] = True

    await update.message.reply_text(
        "🛠 *Admin Panel*\n\nSelect an option:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(ADMIN_KEYBOARD, resize_keyboard=True)
    )

async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_stats()

    msg = (
        "📊 *Church Bot Dashboard*\n\n"
        f"👥 Members: {stats['members']}\n"
        f"🙏 Prayer Requests: {stats['prayers']}\n"
        f"💬 Counseling Requests: {stats['counsel']}\n"
        f"📝 Testimonies: {stats['testimonies']}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_broadcast_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "broadcast"
    await update.message.reply_text("📢 Type your broadcast message:")

async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)

    df_members = pd.read_sql("SELECT * FROM members", conn)
    df_prayers = pd.read_sql("SELECT * FROM prayer_requests", conn)
    df_counsel = pd.read_sql("SELECT * FROM counseling_requests", conn)
    df_testimony = pd.read_sql("SELECT * FROM testimonies", conn)

    filename = f"church_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df_members.to_excel(writer, sheet_name="Members", index=False)
        df_prayers.to_excel(writer, sheet_name="Prayer Requests", index=False)
        df_counsel.to_excel(writer, sheet_name="Counseling", index=False)
        df_testimony.to_excel(writer, sheet_name="Testimonies", index=False)

    conn.close()

    await update.message.reply_document(open(filename, "rb"))
    await update.message.reply_text("✅ Data export complete.")

async def admin_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await start(update, context)

# ======================= HANDLERS ========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["⛪ Church Info", "📅 Service Times"],
        ["🙏 Prayer Request", "💬 Counseling"],
        ["📖 Ask Bible Question", "📝 Testimony"],
        ["🧾 Register", "📞 Contact"]
    ]

    await update.message.reply_text(
        f"🙏 *Welcome to {CHURCH_NAME}*\n\n"
        "I am your intelligent church assistant.\n"
        "How may I help you today?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def prayer_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "prayer"
    await update.message.reply_text("🙏 Please type your prayer request:")

async def counseling_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "counsel"
    await update.message.reply_text("💬 Please explain your situation for counseling:")

async def bible_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "bible"
    await update.message.reply_text("📖 Please type your Bible question or scripture reference:")

async def testimony_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "testimony"
    await update.message.reply_text("📝 Please share your testimony:")

async def register_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "register"
    await update.message.reply_text("🧾 Send in this format:\nFull Name, Phone Number")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    text = update.message.text
    uid = update.effective_user.id
    admin = context.user_data.get("admin")

    # ---------- ADMIN LOGIC ----------

    if admin:

        if text == "📊 Dashboard":
            await admin_dashboard(update, context)
            return

        elif text == "📢 Broadcast":
            await admin_broadcast_prompt(update, context)
            return

        elif text == "📥 Export Data":
            await admin_export(update, context)
            return

        elif text == "❌ Exit Admin":
            await admin_exit(update, context)
            return

        elif mode == "broadcast":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            users = c.execute("SELECT DISTINCT user_id FROM members").fetchall()

            sent = 0
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user[0],
                        text=f"📢 *Church Announcement*\n\n{text}",
                        parse_mode="Markdown"
                    )
                    sent += 1
                except:
                    pass

            conn.close()
            context.user_data.pop("mode", None)

            await update.message.reply_text(f"✅ Broadcast sent to {sent} members.")
            return

        return

    # ---------- NORMAL USER LOGIC ---------

    if mode == "prayer":
        insert("prayer_requests", uid, text)
        await update.message.reply_text("🙏 Your prayer request has been received. God bless you.")
        context.user_data.pop("mode", None)

    elif mode == "counsel":
        await context.bot.send_chat_action(update.effective_chat.id, "typing")
        insert("counseling_requests", uid, text)
        reply = generate_ai_response(text)
        await update.message.reply_text(reply)
        context.user_data.pop("mode", None)

    elif mode == "bible":
        await context.bot.send_chat_action(update.effective_chat.id, "typing")
        reply = generate_ai_response(text)
        await update.message.reply_text(reply)

    elif mode == "testimony":
        insert("testimonies", uid, text)
        await update.message.reply_text("📝 Thank you for sharing your testimony. To God be the glory!")
        context.user_data.pop("mode", None)

    elif mode == "register":
        try:
            name, phone = text.split(",")
            register_member(uid, name.strip(), phone.strip())
            await update.message.reply_text("✅ Registration successful. Welcome to the family!")
            context.user_data.pop("mode", None)
        except:
            await update.message.reply_text("❌ Incorrect format.\nUse: Full Name, Phone Number")

    elif mode == "broadcast":
        if text in ["❌ Exit Admin", "📥 Export Data", "📊 Dashboard", "📢 Broadcast"]:
            return

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        users = c.execute("SELECT DISTINCT user_id FROM members").fetchall()

        sent = 0
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user[0],
                    text=f"📢 *Church Announcement*\n\n{text}",
                    parse_mode="Markdown"
                )
                sent += 1
            except:
                pass

        conn.close()
        await update.message.reply_text(f"✅ Broadcast sent to {sent} members.")
        context.user_data.pop("mode", None)

    else:
        await context.bot.send_chat_action(update.effective_chat.id, "typing")
        reply = generate_ai_response(text)
        await update.message.reply_text(reply)

# ========================= MAIN ==========================

def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    app.add_handler(MessageHandler(filters.Regex("^🙏 Prayer Request$"), prayer_prompt))
    app.add_handler(MessageHandler(filters.Regex("^💬 Counseling$"), counseling_prompt))
    app.add_handler(MessageHandler(filters.Regex("^📖 Ask Bible Question$"), bible_prompt))
    app.add_handler(MessageHandler(filters.Regex("^📝 Testimony$"), testimony_prompt))
    app.add_handler(MessageHandler(filters.Regex("^🧾 Register$"), register_prompt))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("🤖 Church AI Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
