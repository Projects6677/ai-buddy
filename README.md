# 🤖 AI Buddy – WhatsApp AI Assistant

AI Buddy is an intelligent, menu-driven WhatsApp chatbot powered by Python (Flask) and the **WhatsApp Business Cloud API**. It acts as your smart assistant for reminders, grammar correction, translation, file conversions, expense tracking, email writing, currency conversion, weather updates, and more — all through WhatsApp!

---

## 🌟 Features

### 🧠 1. Reminder Bot  
Set reminders using natural language:  
`Remind me to call John tomorrow at 4pm`

### ✍️ 2. Grammar Fixer  
Correct English grammar using **Grok AI API**.

### 💬 3. Ask Me Anything  
General Q&A chatbot powered by Grok AI.

### 📁 4. File/Text Conversion Suite  
Convert between:
- 📄 PDF ➡️ Text
- 📝 Text ➡️ PDF
- 📄 PDF ➡️ Word
- 📝 Text ➡️ Word

### 🌍 5. Translator  
Translate text (custom logic currently placeholder).

### ⛅ 6. Weather Bot  
Get live weather updates for any city using OpenWeather API.

### 💱 7. Currency Converter  
Convert currencies via natural language queries using Grok + custom API.

### 📧 8. AI Email Assistant  
Create professional emails through guided questions and smart AI generation and editing.

### 📊 Hidden Feature – Expense Tracker  
Tell the bot what you spent (e.g. "I spent 300 on pizza at Dominos") and later export your data as an Excel sheet.

---

## 🔌 WhatsApp API Integration

- **WhatsApp Business Cloud API**
  - Webhook receives and responds to messages, documents, media
  - Smart session-based interactions
- **UptimeRobot**
  - Keeps server alive by pinging `/`

---

## 🧰 Tech Stack

| Component          | Tech Used                               |
|--------------------|------------------------------------------|
| Backend            | Python (Flask)                           |
| Messaging API      | WhatsApp Business Cloud API              |
| Grammar Fix        | Grok AI                                  |
| File Conversion    | FPDF, PyMuPDF, pdf2docx, python-docx     |
| Weather API        | OpenWeatherMap                           |
| Currency Conversion| Custom + Grok AI parsing                 |
| AI Email Builder   | Grok AI (parse, analyze, edit, write)    |
| Excel Export       | Pandas, openpyxl                         |

---

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/ai-buddy.git
cd ai-buddy
```

### 2. Setup `.env`
Create a `.env` file with your keys:
```
VERIFY_TOKEN=your_token
ACCESS_TOKEN=your_whatsapp_token
PHONE_NUMBER_ID=your_whatsapp_number_id
GROK_API_KEY=your_grok_key
OPENWEATHER_API_KEY=your_openweather_key
EMAIL_ADDRESS=your_email
EMAIL_PASSWORD=your_password
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the Flask Server
```bash
python app.py
```

---

## 🗂️ Folder Structure
```
ai-buddy/
├── app.py                   # Main Flask app
├── grok_ai.py               # AI functions: grammar, emails, intent parsing
├── email_sender.py          # Email sending logic
├── currency.py              # Currency conversion
├── user_data.json           # Local user data and expenses
├── uploads/                 # Temp storage for file processing
├── requirements.txt
└── README.md
```

---

## 💡 How It Works
1. User sends a message (e.g., “hi”) to the bot.
2. Flask receives webhook and replies with a smart menu.
3. Users reply with numbers or commands (e.g., "2", "remind me").
4. Bot processes input using AI + logic and responds.
5. For documents, the bot downloads, processes, and sends results back.

---

## 🔐 Notes
- Do NOT hardcode API keys — use `.env` securely.
- Use `os.getenv()` in your code for config access.

---

## 🚀 Future Plans
- Voice note to text
- Google Calendar integration for reminders
- Image captioning (via Vision models)
- Support for group chats

---

Built by **Dhruvin** – passionate about using AI to create real-world assistants that solve everyday problems with a touch of fun 🤖✨
