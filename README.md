# 📰 AI News Analyzer

A full-stack AI-powered application that fetches, analyzes, and presents news articles with a modern interface. Built with **FastAPI** for the backend and **Next.js (React + Tailwind CSS)** for the frontend, the app offers multi-language support, AI-based summarization, and abusive content detection.

---

## 🚀 Features

- 🔍 **Fetch News**: Aggregates news from various sources using RSS feeds.
- 🧠 **AI Analysis**: Summarizes and analyzes news content using machine learning.
- 🌐 **Multi-language Support**: English, Hindi, and Kannada.
- 📅 **Date Filtering**: View news from today, this week, or select a custom date.
- 🔑 **Keyword Search**: Search articles by specific keywords.
- ⚠️ **Abusive Content Detection**: Flags and highlights sensitive content.
- 🌙 **Modern UI**: Clean, responsive, dark-themed UI with Tailwind CSS.

---

## 🧰 Tech Stack

| Layer        | Technologies Used                         |
|--------------|--------------------------------------------|
| **Backend**  | FastAPI, Python, Uvicorn                   |
| **Frontend** | Next.js, React, Tailwind CSS, TypeScript   |
| **AI/ML**    | Google Generative AI, scikit-learn         |
| **Others**   | BeautifulSoup, feedparser, requests        |

---

## 📦 Getting Started

### 🖥️ Prerequisites

- Python 3.8+
- Node.js 18+
- `npm` or `yarn`

---

### ⚙️ Backend Setup

```bash
cd backend
python -m venv venv          # (optional)
source venv/bin/activate     # Activate virtual environment
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
API will run at: http://localhost:8000 cd news-analyzer-frontend
npm install                  # or yarn install
npm run dev                  # or yarn dev
App will be available at: http://localhost:3000 
Project Structure
news_analyser/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── news-analyzer-frontend/
│   ├── app/
│   ├── components/
│   ├── package.json
│   └── tailwind.config.js
└── README.md
🙋‍♂️ Author

Arth Rawat – @iasar24