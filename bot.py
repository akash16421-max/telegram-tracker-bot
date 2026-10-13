import sqlite3
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === अपनी डिटेल्स यहाँ डालें ===
BOT_TOKEN = "8689544065:AAEaouAETJKUte9SRuYa1zx0iNtNsKxcrrs"
YOUR_CHAT_ID = 874753114

def init_db():
    conn = sqlite3.connect("tracker.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at DATE NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            progress TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "नमस्ते! आपका टारगेट ट्रैकर बोट तैयार है।\n\n"
        "📌 *कमांड्स:*\n"
        "• `/add <टास्क>` - नया टारगेट जोड़ें\n"
        "• `/tasks` - आज के टारगेट्स देखें\n"
        "• `/done <नंबर>` - टारगेट पूरा मार्क करें\n"
        "• `/read <विषय> <कहाँ तक पढ़ा>` - रीडिंग प्रोग्रेस नोट करें\n"
        "• `/reading` - पढ़ाई की स्थिति देखें\n"
        "• `/report` - 7 दिनों की वीकली रिपोर्ट"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_text = " ".join(context.args)
    if not task_text:
        await update.message.reply_text("कृपया टारगेट भी लिखें। जैसे:\n`/add मॉडर्न हिस्ट्री चैप्टर 1`", parse_mode="Markdown")
        return

    today = datetime.now().date()
    conn = sqlite3.connect("tracker.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (task, created_at) VALUES (?, ?)", (task_text, today))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ टारगेट नोट कर लिया: *{task_text}*", parse_mode="Markdown")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().date()
    conn = sqlite3.connect("tracker.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, task, status FROM tasks WHERE created_at = ?", (today,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("आज के लिए कोई टारगेट सेट नहीं है। `/add` से जोड़ें।", parse_mode="Markdown")
        return

    msg = "📋 *आज के टारगेट्स:*\n\n"
    for row in rows:
        status_icon = "✅" if row[2] == 'completed' else "⏳"
        msg += f"{row[0]}. {status_icon} {row[1]} ({row[2]})\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("टास्क का नंबर लिखें। जैसे: `/done 1`", parse_mode="Markdown")
        return

    try:
        task_id = int(context.args[0])
        conn = sqlite3.connect("tracker.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"शाबाश! टारगेट #{task_id} पूरा हो गया! 🎉")
    except ValueError:
        await update.message.reply_text("कृपया सही नंबर डालें।")

async def update_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("फॉर्मेट: `/read <विषय> <प्रोग्रेस>`\nजैसे: `/read पॉलिटी पेज 50`", parse_mode="Markdown")
        return

    subject = context.args[0]
    progress = " ".join(context.args[1:])
    conn = sqlite3.connect("tracker.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reading_log (subject, progress) VALUES (?, ?)", (subject, progress))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"📖 *{subject}* अपडेट हो गया: _{progress}_", parse_mode="Markdown")

async def get_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("tracker.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subject, progress, updated_at 
        FROM reading_log 
        WHERE id IN (SELECT MAX(id) FROM reading_log GROUP BY subject)
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("अभी कोई रीडिंग डेटा सेव नहीं है।")
        return

    msg = "📚 *पढ़ाई की पिछली प्रोग्रेस:*\n\n"
    for row in rows:
        msg += f"• *{row[0]}*: {row[1]}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    conn = sqlite3.connect("tracker.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM tasks WHERE created_at >= ? GROUP BY status", (week_ago,))
    rows = cursor.fetchall()
    conn.close()

    total = 0
    completed = 0
    for status, count in rows:
        total += count
        if status == 'completed':
            completed = count

    pending = total - completed
    percentage = (completed / total * 100) if total > 0 else 0

    report = (
        f"📊 *पिछले 7 दिनों की वीकली रिपोर्ट*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎯 कुल टारगेट्स: *{total}*\n"
        f"✅ पूरे किए: *{completed}*\n"
        f"⏳ बाकी रह गए: *{pending}*\n"
        f"📈 सफलता दर: *{percentage:.1f}%*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )
    if percentage >= 80:
        report += "शानदार प्रदर्शन! 🔥"
    elif percentage >= 50:
        report += "अच्छा चल रहा है, थोड़ा और जोर लगाएं! 👍"
    else:
        report += "टारगेट्स पूरे करने पर ध्यान दें! ⚠️"

    await update.message.reply_text(report, parse_mode="Markdown")

def main():
    init_db()
    builder = ApplicationBuilder()
    builder = builder.token(BOT_TOKEN)
    builder = builder.connect_timeout(30.0)
    builder = builder.read_timeout(30.0)
    app = builder.build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_task))
    app.add_handler(CommandHandler("tasks", list_tasks))
    app.add_handler(CommandHandler("done", complete_task))
    app.add_handler(CommandHandler("read", update_reading))
    app.add_handler(CommandHandler("reading", get_reading))
    app.add_handler(CommandHandler("report", weekly_report))

    print("बॉट चालू हो चुका है... (Testing mode)")
    app.run_polling()

if __name__ == "__main__":
    main()