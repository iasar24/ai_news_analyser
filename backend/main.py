from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sys
import os

# Add the parent directory to Python path to import the news analyzer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_news2 import fetch_rss_news, analyze_news

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NewsResponse(BaseModel):
    items: List[dict]
    analysis: Optional[str] = None

@app.get("/api/news")
async def get_news(
    language_code: str = Query(..., description="Language code (en, hi, kn)"),
    search_keyword: Optional[str] = Query(None, description="Search keyword"),
    date_option: str = Query(..., description="Date option (Latest News (Today), Latest News (This Week), Custom Date)"),
    year: Optional[int] = Query(None, description="Year for custom date (e.g., 2024)"),
    month: Optional[str] = Query(None, description="Month name for custom date (e.g., january)"),
    day: Optional[int] = Query(None, description="Day for custom date (1-31)")
):
    try:
        # Convert date_option to days_back
        days_back = 1 if date_option == "Latest News (Today)" else 7 if date_option == "Latest News (This Week)" else 0

        # Fetch news using the existing function
        news_items = fetch_rss_news(
            language=language_code,
            days_back=days_back,
            search_keyword=search_keyword,
            use_ai_analysis=True  # Enable AI analysis by default
        )

        # If custom date specified, further filter news_items by exact date
        if date_option == "Custom Date" and year and month and day:
            try:
                month_num = datetime.strptime(month.capitalize(), "%B").month
                selected_date = datetime(year, month_num, day)
                news_items = [item for item in news_items if item.get("pub_date") and item["pub_date"].date() == selected_date.date()]
            except ValueError:
                # Invalid month name provided; ignore filtering
                pass

        # Get AI analysis
        analysis = analyze_news(news_items) if news_items else None

        return NewsResponse(
            items=news_items,
            analysis=analysis
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 