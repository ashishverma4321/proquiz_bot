import os
import random
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, PollHandler
import asyncio

# Load secrets from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

user_quiz = {}
subjects = ["General Knowledge", "Electronics", "Mathematics", "Reasoning"]

# Get question from OpenAI
async def get_ai_question(subject):
    prompt = f"Generate one multiple-choice question for {subject} in Hindi for a UP government exam. Include 4 options, correct answer index (0-3), and a 100-word explanation in Hindi. Format as JSON with keys: question, options, answer, explanation."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return eval(response["choices"][0]["message"]["content"])
    except Exception as e:
        print("OpenAI Error:", e)
        return None

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    user_quiz[user_id] = {
        "questions": [],
        "index": 0,
        "chat_id": chat_id
    }

    for _ in range(150):
        subject = random.choice(subjects)
        question = await get_ai_question(subject)
        if question:
            user_quiz[user_id]["questions"].append(question)

    await send_next_question(user_id, context)

# Send poll
async def send_next_question(user_id, context):
    quiz = user_quiz.get(user_id)
    if not quiz or quiz["index"] >= len(quiz["questions"]):
        await context.bot.send_message(chat_id=quiz["chat_id"], text="🎉 Quiz समाप्त हुआ!")
        return

    q = quiz["questions"][quiz["index"]]
    poll_message = await context.bot.send_poll(
        chat_id=quiz["chat_id"],
        question=q["question"],
        options=q["options"],
        type="quiz",
        correct_option_id=q["answer"],
        is_anonymous=False,
        open_period=15
    )

    quiz["poll_id"] = poll_message.poll.id
    quiz["message_id"] = poll_message.message_id

# Handle poll answer
async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.poll_answer.user.id
    quiz = user_quiz.get(user_id)
    if not quiz:
        return

    index = quiz["index"]
    q = quiz["questions"][index]
    selected = update.poll_answer.option_ids[0]
    correct = q["answer"]

    explanation = q.get("explanation", "कोई व्याख्या उपलब्ध नहीं है।")
    msg = "✅ सही उत्तर!\n" if selected == correct else f"❌ गलत उत्तर! सही उत्तर: {q['options'][correct]}\n"
    msg += f"📘 व्याख्या:\n{explanation}"

    await context.bot.send_message(chat_id=quiz["chat_id"], text=msg)

    quiz["index"] += 1
    await asyncio.sleep(1)
    await send_next_question(user_id, context)

# Bot Setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(PollHandler(handle_poll_answer))

if __name__ == "__main__":
    print("🤖 Bot चालू हो रहा है...")
    app.run_polling()
