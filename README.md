# Advanced News Analyzer

A modern news aggregator and analyzer with AI-powered content analysis and a beautiful dark-themed UI.

## Features

- Multi-language news support (English, Hindi, Kannada)
- Real-time news fetching from multiple sources
- AI-powered content analysis using Google's Gemini
- Content sensitivity detection
- Beautiful dark-themed UI with image previews
- Responsive design for all devices

## Setup

### Frontend (Next.js)

1. Navigate to the frontend directory:
```bash
cd news-analyzer-frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env.local` file with your API keys:
```
UNSPLASH_ACCESS_KEY=your_unsplash_api_key
PYTHON_BACKEND_URL=http://localhost:8000
```

4. Start the development server:
```bash
npm run dev
```

### Backend (FastAPI)

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys:
```
GEMINI_API_KEY=your_gemini_api_key
```

5. Start the backend server:
```bash
python main.py
```

## Usage

1. Open your browser and navigate to `http://localhost:3000`
2. Select your preferred language
3. Choose a date range
4. Optionally enter a search keyword
5. Click "Scrap News" to fetch the latest news
6. Use the "Analyze with Gemini" button for AI-powered analysis
7. Generate PDF reports of your news collection

## Technologies Used

- Frontend:
  - Next.js 14
  - TypeScript
  - Tailwind CSS
  - Unsplash API for images

- Backend:
  - FastAPI
  - Google Gemini AI
  - BeautifulSoup4
  - Feedparser

## Contributing

Feel free to open issues and pull requests for any improvements you'd like to add.

## License

MIT 