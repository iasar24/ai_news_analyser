AI News Analyzer
A full-stack application that fetches, analyzes, and presents news articles using AI. The backend is built with FastAPI and the frontend uses Next.js (React + Tailwind CSS). The app supports multiple languages, date filtering, keyword search, and provides AI-powered news analysis.
Features
Fetch News: Aggregates news from various sources via RSS feeds.
AI Analysis: Summarizes and analyzes news content using AI.
Multi-language Support: English, Hindi, Kannada.
Date Filtering: View news from today, this week, or a custom date.
Keyword Search: Search for news articles by keyword.
Abusive Content Detection: Flags and highlights sensitive content.
Modern UI: Responsive, dark-themed interface with Tailwind CSS.
Tech Stack
Backend: FastAPI, Python, Uvicorn
Frontend: Next.js, React, Tailwind CSS, TypeScript
AI/ML: Google Generative AI, scikit-learn
Other: BeautifulSoup, feedparser, requests
Getting Started
Prerequisites
Python 3.8+
Node.js 18+
npm or yarn Backend Setup
1. Navigate to the backend directory:
README.md 1/6 v
cd backend
2. Create a virtual environment (optional but recommended):
README.md 1/6 v
python -m venv venv source venv/bin/activate
3. Install dependencies:
README.md +1 -1 •
Python 3.8+
Node. js 18+ npm or yarn
cd backend cd
backend
4. Run the backend server:
README.md No changes made
uvicorn main:app --reload --host 0.0.0.0 --port 8000
The API will be available at http://localhost: 8000 . Frontend Setup
1. Navigate to the frontend directory:
README.md No changes made
cd
news-analyzer-frontend
2. Install dependencies:
README.md No changes made
npm install
# or
yarn install
3. Run the development server:
$
bash
npm run dev
# or
yarn dev
The app will be available at http://localhost: 3000.
Run Usage
• Open the frontend in your browser.
• Select a language (English, Hindi, Kannada).
• Choose a date range (Today, This Week, or Custom Date).
• Enter a keyword to search for specific news.
• View news cards, Al-generated analysis, and abusive content warnings.
API Overview
• GET /api/news (Backend)
• Query params:
• language_code: en, hi, kn
• search_keyword: (optional)
• date_option: Latest News (Today), Latest News (This Week), Custom Date
• year, month, day: (for custom date)
• Returns: List of news items and Al analysis. Project Structure
= text
• Apply to README.md
backend/ main. py
requirements.txt
news-analyzer-frontend/
app/ components/ package. json
tailwind. config.js
requirements.txt
README. md
# FastAPI backend
# Next.js frontend
# (root, possibly legacy)
License
This project is for educational purposes.
Let me know if you want to add badges, deployment instructions, or more details!