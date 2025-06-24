# 🤖 AI Buddy – WhatsApp AI Assistant

AI Buddy is an intelligent, menu-driven WhatsApp chatbot built using Python (Flask) and integrated with the **WhatsApp Business Cloud API**. It acts as your smart assistant for reminders, grammar correction, translation, document conversions, AI Q&A, weather updates, and more — all via WhatsApp!

---

## 🌟 Features

### 🧠 1. Reminder Bot  
Set reminders using natural language:  
`Remind me to attend class at 6 PM`

### 📖 2. Grammar Fixer  
Fix incorrect English grammar using Grok AI (via API).

### 💬 3. Ask Me Anything  
General AI chatbot with custom logic for Q&A, fun facts, and more.

### 📁 4. File/Text Conversion Suite  
Convert files in multiple formats:
- 📄 PDF ➡️ Text
- 📄 Word (.docx) ➡️ PDF
- 📝 Text ➡️ PDF
- 📄 PDF ➡️ Word (.docx)

### 🌍 5. Translator  
Translate between:
- English to French (`en: I love programming`)
- French to English (`fr: J’aime coder`)

(Uses Hugging Face Helsinki-NLP translation models)

### ⛅ 6. Weather Bot  
Instant weather info based on city name.

---

## 🔌 WhatsApp API Integration

This project uses:

- **WhatsApp Business Cloud API**
  - Integrated via **Webhook Endpoint**
  - Handles incoming messages, media, and user sessions
- **UptimeRobot**:
  - Keeps the Flask server live 24/7 by pinging the `/` endpoint periodically

---

## 🧰 Tech Stack

| Component          | Tech Used                             |
|--------------------|----------------------------------------|
| Backend            | Python (Flask)                         |
| Messaging API      | WhatsApp Business Cloud API            |
| Grammar Fix        | Grok AI                                |
| Translation        | Hugging Face (Helsinki-NLP models)     |
| File Conversion    | FPDF, PyMuPDF, pdf2docx, docx2pdf      |
| OCR (PDF to Text)  | pytesseract                            |
| Uptime Monitoring  | UptimeRobot                            |

---

## 📦 Installation

### 1. Clone the Repository
git clone https://github.com/yourusername/ai-buddy.git
cd ai-buddy
2. Create a .env File
env
Copy
Edit
HUGGINGFACE_API_KEY=your_huggingface_token
3. Install Dependencies
bash
Copy
Edit
pip install -r requirements.txt
4. Start the Flask Server
bash
Copy
Edit
python app.py
🗂️ Folder Structure
bash
Copy
Edit
ai-buddy/
│
├── app.py                   # Main Flask app
├── ai.py                    # AI question-answer logic
├── grok_ai.py               # Grammar correction using Grok
├── reminders.py             # Reminder scheduling
├── translator_module.py     # Text translation
├── weather.py               # Weather API logic
├── user_data.json           # Stores user sessions
├── requirements.txt
└── README.md
💬 How It Works
User sends a message like hi or start on WhatsApp.

The Flask app (running on Render or locally with ngrok/UptimeRobot) receives a webhook.

Bot replies with a menu and handles stateful logic using user_sessions.

Users interact and receive smart replies or files.

🔐 Notes
Do not hardcode ACCESS_TOKEN or HUGGINGFACE_API_KEY in public repos.

Use .env + os.getenv for secure management.

🚀 Future Upgrades
Add voice note to text (speech recognition)

Schedule daily message notifications

Store reminders on Google Calendar

Support image captioning with Vision models

Dhruvin – A creative developer passionate about building useful and fun AI-powered applications for real-world use.
