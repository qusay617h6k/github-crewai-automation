from fastapi import FastAPI, Request
from crewai import Agent, Task, Crew
import requests
import os
import uvicorn

app = FastAPI()

# جلب المفاتيح من البيئة السحابية لحمايتها
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # أو أي نموذج مجاني تستخدمه

# إعداد وكيل CrewAI
classifier_agent = Agent(
    role="GitHub Issue Classifier",
    goal="Classify the issue accurately into bug, feature-request, or documentation.",
    backstory="You are an advanced AI assistant built to read GitHub developer issues and label them.",
    verbose=True
)

def create_task(title, body):
    return Task(
        description=f"Analyze this GitHub issue:\nTitle: {title}\nBody: {body}",
        expected_output="Strictly one word in lowercase: either 'bug', 'feature-request', or 'documentation'.",
        agent=classifier_agent
    )

# نقطة استقبال بيانات جيتهاب
@app.post("/github-webhook")
async def github_webhook(request: Request):
    payload = await request.json()
    
    # التأكد أن الحدث هو فتح Issue جديدة
    if payload.get("action") == "opened":
        issue_title = payload["issue"]["title"]
        issue_body = payload["issue"]["body"]
        issue_url = payload["issue"]["html_url"]
        repo_name = payload["repository"]["full_name"]
        
        # تشغيل ذكاء CrewAI لتصنيف الإيشو
        task = create_task(issue_title, issue_body)
        crew = Crew(agents=[classifier_agent], tasks=[task])
        classification_result = str(crew.kickoff()).strip().lower()
        
        # إرسال التنبيه الفوري لقصي على تليجرام
        send_telegram_message(classification_result, issue_title, repo_name, issue_url)
        
        return {"status": "success", "classified_as": classification_result}

    return {"status": "ignored"}

def send_telegram_message(label, title, repo, url):
    emoji = "🐛 Bug" if label == "bug" else ("✨ Feature" if label == "feature-request" else "📝 Docs")
    
    text = (
        f"🔔 *تنبيه أتمتة GitHub جديد!*\n\n"
        f"📦 *المستودع:* {repo}\n"
        f"📌 *المشكلة:* {title}\n"
        f"🏷️ *التصنيف التلقائي:* `{emoji}`\n\n"
        f"🔗 [اضغط هنا لفتح الـ Issue في GitHub]({url})"
    )
    
    telegram_url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(telegram_url, json=payload)

if __name__ == "__main__":
    # تشغيل السيرفر على بورت متوافق مع السيرفرات السحابية
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
