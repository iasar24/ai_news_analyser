import streamlit as st
from bs4 import BeautifulSoup
import requests
import feedparser
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
import re
import hashlib
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Advanced News Scraper",
    page_icon="🌐",
    layout="wide"
)

# Define abusive keywords to detect
ABUSIVE_KEYWORDS = [
    "kill", "murder", "assault", "attack", "hate", "violent", "terror", 
    "bomb", "shoot", "racist", "abuse", "threat", "harass"
]

# Define news sources
NEWS_SOURCES = [
    {"name": "CNN", "rss": "http://rss.cnn.com/rss/cnn_topstories.rss", "language": "en"},
    {"name": "BBC", "rss": "http://feeds.bbci.co.uk/news/rss.xml", "language": "en"},
    {"name": "Reuters", "rss": "http://feeds.reuters.com/reuters/topNews", "language": "en"},
    {"name": "NPR", "rss": "https://feeds.npr.org/1001/rss.xml", "language": "en"},
    {"name": "The Guardian", "rss": "https://www.theguardian.com/world/rss", "language": "en"},
    # Hindi sources
    {"name": "Jagran", "rss": "https://www.jagran.com/rss/news-national.xml", "language": "hi"},
    {"name": "Dainik Bhaskar", "rss": "https://www.bhaskar.com/rss-v1--category-1740.xml", "language": "hi"},
    # Kannada sources
    {"name": "Vijaya Karnataka", "rss": "https://vijaykarnataka.com/rss", "language": "kn"},
    {"name": "Prajavani", "rss": "https://www.prajavani.net/feed", "language": "kn"},
    {"name": "Udayavani", "rss": "https://www.udayavani.com/feed", "language": "kn"},
]

def highlight_abusive_words(text):
    """Highlight abusive words in the text"""
    for word in ABUSIVE_KEYWORDS:
        pattern = re.compile(r'\b' + word + r'\b', re.IGNORECASE)
        text = pattern.sub(f'<span style="color:red;font-weight:bold">{word}</span>', text)
    return text

def highlight_search_keyword(text, keyword):
    """Highlight search keyword in the text"""
    if not keyword:
        return text
    pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
    return pattern.sub(f'<span style="color:green;font-weight:bold">{keyword}</span>', text)

def get_news_hash(title):
    """Generate a hash for a news title to identify duplicates"""
    return hashlib.md5(title.lower().encode()).hexdigest()

def fetch_rss_news(language="en", days_back=1, search_keyword=None):
    """Fetch news from RSS feeds based on selected language"""
    all_news = []
    
    # Calculate the date threshold for recent news
    date_threshold = datetime.now() - timedelta(days=days_back)
    
    for source in NEWS_SOURCES:
        if source["language"] == language:
            try:
                feed = feedparser.parse(source["rss"])
                for entry in feed.entries[:20]:  # Increased limit to get more recent news
                    title = entry.title
                    link = entry.link
                    description = entry.description if hasattr(entry, 'description') else ""
                    
                    # Parse the published date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6])
                    
                    # Skip if not recent enough and we have a date
                    if pub_date and pub_date < date_threshold:
                        continue
                    
                    # Skip if search keyword is provided and not in title or description
                    if search_keyword and search_keyword.lower() not in title.lower() and search_keyword.lower() not in description.lower():
                        continue
                    
                    # Create a unique hash for this news item
                    news_hash = get_news_hash(title)
                    
                    all_news.append({
                        "title": title,
                        "link": link,
                        "description": description,
                        "source": source["name"],
                        "hash": news_hash,
                        "has_abusive": any(re.search(r'\b' + word + r'\b', title, re.IGNORECASE) for word in ABUSIVE_KEYWORDS),
                        "pub_date": pub_date
                    })
            except Exception as e:
                st.warning(f"Error fetching from {source['name']}: {str(e)}")
    
    # Remove duplicates based on hash
    unique_news = []
    seen_hashes = set()
    
    for news in all_news:
        if news["hash"] not in seen_hashes:
            seen_hashes.add(news["hash"])
            unique_news.append(news)
    
    # Sort by publication date (newest first)
    # Use a default datetime for items with None pub_date
    # Sort by publication date (newest first)
    unique_news.sort(key=lambda x: x.get("pub_date") or datetime.min, reverse=True)   
    
    return unique_news

def generate_pdf(news_items, date_str, language, search_keyword=None):
    """Generate a PDF report of news items"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        alignment=1  # Center alignment
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        textColor=colors.blue
    )
    
    news_style = ParagraphStyle(
        'NewsStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=6
    )
    
    source_style = ParagraphStyle(
        'SourceStyle',
        parent=styles['Italic'],
        fontSize=10,
        textColor=colors.gray,
        spaceAfter=12
    )
    
    link_style = ParagraphStyle(
        'LinkStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.blue,
        spaceAfter=15
    )
    
    # Create the content
    content = []
    
    # Add title
    lang_name = {"en": "English", "hi": "Hindi", "kn": "Kannada"}
    content.append(Paragraph(f"News Report - {date_str}", title_style))
    content.append(Paragraph(f"Language: {lang_name.get(language, 'Unknown')}", subtitle_style))
    
    if search_keyword:
        content.append(Paragraph(f"Keyword Search: '{search_keyword}'", subtitle_style))
    
    content.append(Spacer(1, 12))
    
    # Add abusive content warning if needed
    has_abusive = any(news["has_abusive"] for news in news_items)
    if has_abusive:
        warning_style = ParagraphStyle(
            'WarningStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.red,
            spaceAfter=12,
            borderWidth=1,
            borderColor=colors.red,
            borderPadding=5,
            borderRadius=5
        )
        content.append(Paragraph("⚠️ WARNING: This report contains potentially sensitive content highlighted in red", warning_style))
        content.append(Spacer(1, 12))
    
    # Add news items
    for i, news in enumerate(news_items, 1):
        # Check for abusive words and highlight them
        title = news["title"]
        for word in ABUSIVE_KEYWORDS:
            if re.search(r'\b' + word + r'\b', title, re.IGNORECASE):
                title = title.replace(word, f'<font color="red"><b>{word}</b></font>')
        
        # Highlight search keyword if provided
        if search_keyword and search_keyword.lower() in title.lower():
            title = title.replace(search_keyword, f'<font color="green"><b>{search_keyword}</b></font>')
        
        # Add the news item
        content.append(Paragraph(f"{i}. {title}", news_style))
        
        # Add publication date if available
        if news.get("pub_date"):
            date_str = news["pub_date"].strftime("%Y-%m-%d %H:%M")
            content.append(Paragraph(f"Published: {date_str}", source_style))
            
        content.append(Paragraph(f"Source: {news['source']}", source_style))
        content.append(Paragraph(f"<a href='{news['link']}'>Read full article</a>", link_style))
        content.append(Spacer(1, 10))
    
    # Build the PDF
    doc.build(content)
    buffer.seek(0)
    return buffer

# Main Streamlit app
st.markdown(
    """
<h1 style='text-align:center'>Advanced News Scraper</h1>
""",
    unsafe_allow_html=True,
)
st.write("##")

# Try to load the image, but handle the case if it's missing
try:
    st.image("news_img.png", use_column_width="auto")
except Exception:
    st.title("📰 News Analyzer Tool")
    st.write("Fetch and analyze news from multiple sources")

st.write("##")

# Date selection
col1, col2 = st.columns(2)

with col1:
    st.write("## Select Date Range: ")
    date_option = st.radio(
        "Choose date option:",
        ["Latest News (Today)", "Latest News (This Week)", "Custom Date"]
    )

    if date_option == "Custom Date":
        year, month, day = st.columns(3)
        year_select = year.selectbox("Select year:", options=["2024", "2023", "2022"])
        month_select = month.selectbox(
            "Select month:",
            options=[
                "january", "february", "march", "april", "may", "june",
                "july", "august", "september", "october", "november", "december",
            ],
        )
        day_select = day.selectbox("Select day: ", options=[str(i) for i in range(1, 32)])
        days_back = 0  # Not used for custom date
    else:
        # Set current date for latest news options
        current_date = datetime.now()
        year_select = str(current_date.year)
        month_select = current_date.strftime("%B").lower()
        day_select = str(current_date.day)
        
        # Set days_back based on selection
        if date_option == "Latest News (Today)":
            days_back = 1
        else:  # Latest News (This Week)
            days_back = 7

with col2:
    # Language selection
    st.write("## Select Options: ")
    language_options = ["English", "Hindi", "Kannada"]
    language_select = st.selectbox("Select Language:", options=language_options)
    language_code = {"English": "en", "Hindi": "hi", "Kannada": "kn"}[language_select]
    
    # Keyword search
    search_keyword = st.text_input("Search for specific keyword in news (optional):")

st.write("##")

# Action buttons
col1, col2 = st.columns(2)
scrap_btn = col1.button("Scrap News")
generate_pdf_btn = col2.button("Generate PDF Report")

# Format date string
str_date = str(day_select)
if str_date[-1] == "1" and str_date != "11":
    date_suffix = "st"
elif str_date[-1] == "2" and str_date != "12":
    date_suffix = "nd"
elif str_date[-1] == "3" and str_date != "13":
    date_suffix = "rd"
else:
    date_suffix = "th"

date_display = f"{day_select}{date_suffix} {month_select}, {year_select}"

if date_option != "Custom Date":
    if date_option == "Latest News (Today)":
        st.write(f"### Today's Latest News")
    else:
        st.write(f"### This Week's Latest News")
else:
    st.write(f"### News for {date_display}")

# Custom styling
box_style = """
    <style>
        .custom-box {
            padding: 10px;
            border: 2px solid white;
            border-radius: 10px;
            background-color: black;
            color: white;
            margin-bottom: 10px;
        }
        .custom-box a {
            color: #00FFFF !important;
            text-decoration: none !important;
            font-weight: bold !important;
        }
        .abusive-word {
            color: red;
            font-weight: bold;
        }
        .search-keyword {
            color: green;
            font-weight: bold;
        }
        .news-source {
            color: #888;
            font-style: italic;
            font-size: 0.8em;
        }
        .news-date {
            color: #aaa;
            font-size: 0.8em;
        }
    </style>
"""
st.markdown(box_style, unsafe_allow_html=True)

# Initialize session state for news
if 'news_items' not in st.session_state:
    st.session_state.news_items = []

# Scrape news when button is clicked
if scrap_btn:
    with st.spinner("Fetching news from multiple sources..."):
        # Get news from RSS feeds
        rss_news = fetch_rss_news(language_code, days_back, search_keyword)
        
        # Get news from sarkaripariksha if language is English or Hindi and using custom date
        sarkari_news = []
        if language_code in ["en", "hi"] and date_option == "Custom Date":
            text_language = "1" if language_code == "en" else "2"
            url = (
                "https://sarkaripariksha.com/gk-and-current-affairs/"
                + year_select
                + "/"
                + month_select
                + "/"
                + str(day_select)
                + "/"
                + text_language
                + "/"
            )
            try:
                req = requests.get(url)
                soup = BeautifulSoup(req.text, "html.parser")
                news_list = soup.find_all("div", class_="examlist-details-img-box")
                
                for news_item in news_list:
                    a_tag = news_item.find("h2").find("a")
                    news_title = a_tag.get_text(strip=True)
                    href_link = a_tag["href"]
                    
                    # Skip if search keyword is provided and not in title
                    if search_keyword and search_keyword.lower() not in news_title.lower():
                        continue
                    
                    news_hash = get_news_hash(news_title)
                    
                    has_abusive = any(re.search(r'\b' + word + r'\b', news_title, re.IGNORECASE) for word in ABUSIVE_KEYWORDS)
                    
                    sarkari_news.append({
                        "title": news_title,
                        "link": href_link,
                        "description": "",
                        "source": "Sarkari Pariksha",
                        "hash": news_hash,
                        "has_abusive": has_abusive,
                        "pub_date": datetime.now()  # Assume current date as publication date
                    })
            except Exception as e:
                st.error(f"Error fetching from Sarkari Pariksha: {str(e)}")
        
        # Combine and deduplicate news
        all_news = rss_news + sarkari_news
        unique_news = []
        seen_hashes = set()
        
        for news in all_news:
            if news["hash"] not in seen_hashes:
                seen_hashes.add(news["hash"])
                unique_news.append(news)
        
        # Sort by publication date (newest first)
        unique_news.sort(key=lambda x: x.get("pub_date")or datetime.min, reverse=True)
        
        st.session_state.news_items = unique_news
        
        if len(unique_news) > 0:
            st.success(f"Found {len(unique_news)} unique news items")
        else:
            if search_keyword:
                st.warning(f"No news found matching the keyword '{search_keyword}'")
            else:
                st.warning("No recent news found. Try adjusting your search criteria.")

# Display news items
if st.session_state.news_items:
    for i, news in enumerate(st.session_state.news_items, 1):
        title = highlight_abusive_words(news["title"])
        if search_keyword:
            title = highlight_search_keyword(title, search_keyword)
        
        date_str = ""
        if news.get("pub_date"):
            date_str = f"<div class='news-date'>Published: {news['pub_date'].strftime('%Y-%m-%d %H:%M')}</div>"
        
        st.markdown(
            f"""<div class="custom-box">
                {i}- <a href="{news['link']}">{title}</a>
                {date_str}
                <div class="news-source">Source: {news['source']}</div>
            </div>""",
            unsafe_allow_html=True,
        )


# Generate PDF report
if generate_pdf_btn and st.session_state.news_items:
    with st.spinner("Generating PDF report..."):
        pdf_buffer = generate_pdf(st.session_state.news_items, date_display, language_code, search_keyword)
        
        # Offer the PDF for download
        file_name = f"news_report_{year_select}_{month_select}_{day_select}_{language_select}"
        if search_keyword:
            file_name += f"_{search_keyword}"
        file_name += ".pdf"
        
        st.download_button(
            label="Download PDF Report",
            data=pdf_buffer,
            file_name=file_name,
            mime="application/pdf"
        )
elif generate_pdf_btn and not st.session_state.news_items:
    st.warning("No news items to generate a PDF report. Please fetch news first.")