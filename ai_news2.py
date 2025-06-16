# -*- coding: utf-8 -*-
import streamlit as st
from bs4 import BeautifulSoup
import requests
import feedparser
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
import re
import hashlib
from datetime import datetime, timedelta
import google.generativeai as genai
from google.generativeai import GenerativeModel
import os
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load environment variables
load_dotenv()

# Configure API keys
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Initialize APIs
gemini_initialized = False
if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        models = genai.list_models()  # Simple check
        gemini_initialized = True
    except ImportError:
        st.error("The 'google-generativeai' library is not installed. Please run 'pip install google-generativeai' in your terminal.", icon="🚨")
    except Exception as e:
        st.error(f"Failed to configure Gemini API: {e}. Check your API key and network connection.", icon="🔥")
else:
    st.warning("Gemini API key not found. Please set the GEMINI_API_KEY environment variable in your .env file to enable AI analysis.", icon="⚠️")

st.set_page_config(
    page_title="Advanced News Scraper",
    page_icon="🌐",
    layout="wide"
)

# Define abusive keywords to detect
# Define abusive keywords to detect in multiple languages
ABUSIVE_KEYWORDS = {
    "en": [
        "kill", "murder", "assault", "attack", "hate", "violent", "terror",
        "bomb", "shoot", "racist", "abuse", "threat", "harass", "genocide",
        "extremist", "rape", "torture", "massacre", "suicide", "riot",
        "hostage", "kidnap", "lynch", "brutal", "bloodshed", "slaughter",
        "militant", "radicalize", "jihad", "supremacist"
    ],
    
    "hi": [
        # Violence related
        "हत्या", "मारना", "हमला", "हिंसा", "आतंक", "बम", "गोली", 
        # Hate speech related
        "नफरत", "नस्लवादी", "दुर्व्यवहार", "धमकी", "परेशान", 
        # More violent terms
        "बलात्कार", "यातना", "नरसंहार", "आत्महत्या", "दंगा",
        # Threats and abuse
        "बंधक", "अपहरण", "लिंचिंग", "क्रूर", "खून", "क़त्ल",
        # Extremism related
        "आतंकवादी", "चरमपंथी", "जिहाद", "हिंसक", "उग्रवादी"
    ],
    
    "kn": [
        # Violence related
        "ಕೊಲೆ", "ಹತ್ಯೆ", "ದಾಳಿ", "ಹಿಂಸೆ", "ಭಯೋತ್ಪಾದನೆ", "ಬಾಂಬ್", "ಗುಂಡು",
        # Hate speech related
        "ದ್ವೇಷ", "ತಾರತಮ್ಯ", "ದುರುಪಯೋಗ", "ಬೆದರಿಕೆ", "ಕಿರುಕುಳ",
        # More violent terms
        "ಅತ್ಯಾಚಾರ", "ಚಿತ್ರಹಿಂಸೆ", "ಸಾಮೂಹಿಕ ಹತ್ಯೆ", "ಆತ್ಮಹತ್ಯೆ", "ಗಲಭೆ",
        # Threats and abuse
        "ಒತ್ತೆ", "ಅಪಹರಣ", "ಲಿಂಚಿಂಗ್", "ಕ್ರೂರ", "ರಕ್ತಪಾತ", "ಕೊಲೆ",
        # Extremism related
        "ಉಗ್ರಗಾಮಿ", "ತೀವ್ರವಾದಿ", "ಜಿಹಾದ್", "ಹಿಂಸಾತ್ಮಕ", "ಭಯೋತ್ಪಾದಕ"
    ]
}

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

def analyze_content_for_abuse(text):
    """Use Gemini to analyze text for abusive content beyond predefined keywords"""
    if not gemini_initialized:
        return False, []
    
    try:
        prompt = f"""Analyze the following text for potentially abusive, harmful, or toxic content. 
        Identify any language that could be considered offensive, threatening, hateful, or inappropriate.
        
        Text to analyze: "{text}"
        
        Return your response in this format:
        - Is_Abusive: [Yes/No]
        - Abusive_Elements: [List specific words, phrases or elements that are problematic]
        - Severity: [Low/Medium/High]
        - Explanation: [Brief explanation]
        """
        
        model = GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=300, temperature=0.2),
            request_options={'timeout': 30}
        )
        
        analysis_text = "".join(part.text for part in response.candidates[0].content.parts).strip()
        
        # Parse the response to extract information
        is_abusive = "is_abusive: yes" in analysis_text.lower()
        
        # Extract abusive elements if any
        abusive_elements = []
        for line in analysis_text.split('\n'):
            if "abusive_elements:" in line.lower():
                elements_text = line.split(':', 1)[1].strip()
                # Remove brackets and split by commas
                elements_text = elements_text.strip('[]')
                abusive_elements = [e.strip() for e in elements_text.split(',') if e.strip()]
        
        return is_abusive, abusive_elements
        
    except Exception as e:
        st.warning(f"Error analyzing content for abuse: {str(e)}")
        return False, []

def highlight_abusive_words(text, languages=["en"], ai_detected_elements=None):
    keywords = []
    for lang in languages:
        keywords += ABUSIVE_KEYWORDS.get(lang, [])
    keywords = list(set(filter(None, keywords)))

    for word in keywords:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        text = pattern.sub(lambda m: f'<span style="color:red;font-weight:bold">{m.group()}</span>', text)

    if ai_detected_elements:
        for element in ai_detected_elements:
            if element and len(element) > 2:
                pattern = re.compile(re.escape(element), re.IGNORECASE)
                text = pattern.sub(lambda m: f'<span style="color:orange;font-weight:bold">{m.group()}</span>', text)

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

def fetch_rss_news(language="en", days_back=1, search_keyword=None, use_ai_analysis=False):
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
                    
                    # Check for abusive content using predefined keywords
                    has_keyword_abuse = any(re.search(r'\b' + word + r'\b', title + " " + description, re.IGNORECASE) for word in ABUSIVE_KEYWORDS)
                    
                    # Check for abusive content using AI (if enabled)
                    ai_abuse_detected = False
                    ai_abuse_elements = []
                    
                    # Only use AI analysis if enabled and keyword detection didn't find anything
                    if use_ai_analysis and not has_keyword_abuse and gemini_initialized:
                        # Combine title and description for analysis
                        full_text = f"{title}. {description}"
                        ai_abuse_detected, ai_abuse_elements = analyze_content_for_abuse(full_text)
                    
                    all_news.append({
                        "title": title,
                        "link": link,
                        "description": description,
                        "source": source["name"],
                        "hash": news_hash,
                        "has_abusive": has_keyword_abuse or ai_abuse_detected,
                        "abusive_elements": ai_abuse_elements,
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
    unique_news.sort(key=lambda x: x.get("pub_date") or datetime.min, reverse=True)   
    
    return unique_news

def analyze_with_gemini(news_items):
    """Analyze news items using Google's Gemini API"""
    if not gemini_initialized:
        return "Gemini API is not configured or initialized. Please check your API key."

    try:
        items_for_analysis = news_items[:15]  # Analyze top 15 items
        if not items_for_analysis:
            return "No news items provided for analysis."

        news_summary = "\n\n".join([
            f"Title: {item['title']}\nSource: {item['source']}\nDescription: {item.get('description', 'No description available')}"
            for item in items_for_analysis
        ]).strip()
        if not news_summary:
            return "Could not generate summary from provided news items."

        prompt = f"""Please analyze the following news headlines and descriptions. Provide a concise analysis covering these points:

1.  **Main Themes:** What are the 2-3 dominant topics or themes emerging from these news items?
2.  **Key Trends/Patterns:** Are there any noticeable trends, recurring events, or patterns?
3.  **Potential Bias/Perspective:** Briefly comment if any significant bias or specific viewpoint is apparent from the headlines provided (acknowledge limitations if based only on headlines).
4.  **Regional/Global Impact:** Briefly mention any potential wider implications (regional or global) suggested by the news.

Keep the overall analysis brief, insightful, and structured (e.g., use bullet points or numbered lists for clarity).

**News Items for Analysis:**
---
{news_summary}
---
**Your Analysis:**
"""
        model = GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=800, temperature=0.6),
            request_options={'timeout': 120}
        )

        analysis_text = ""
        if response.candidates:
            try:
                analysis_text = "".join(part.text for part in response.candidates[0].content.parts).strip()
            except (AttributeError, IndexError):
                pass
        if not analysis_text and hasattr(response, 'text'):
            analysis_text = response.text.strip()
        if not analysis_text and response.parts:
            analysis_text = "".join(part.text for part in response.parts).strip()

        if not analysis_text and hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            reason = response.prompt_feedback.block_reason
            st.error(f"Gemini analysis blocked. Reason: {reason}", icon="🚫")
            return f"Analysis blocked by safety settings or content policy: {reason}"
        elif not analysis_text:
            st.warning("Gemini returned an empty response.", icon="🤔")
            return "Gemini returned an empty response. The prompt might need adjustment or the model could not generate content."

        return analysis_text

    except Exception as e:
        st.error(f"Error during Gemini API call: {str(e)}", icon="🔥")
        if "API key not valid" in str(e):
            return "Invalid Gemini API Key."
        elif "quota" in str(e).lower():
            return "Gemini API Quota exceeded."
        elif "resource has been exhausted" in str(e).lower():
            return "Gemini API resources exhausted (quota)."
        elif "model" in str(e).lower() and ("not found" or "does not exist") in str(e).lower():
            return f"Gemini Model not found or unavailable."
        elif "DeadlineExceeded" in str(e) or "timed out" in str(e).lower():
            return "Gemini API call timed out. Try reducing the number of articles analyzed or check network."
        return f"An unexpected error occurred with Gemini: {str(e)}"

def analyze_news(news_items):
    """Analyze news using the Gemini AI model"""
    if not news_items:
        return "No news items to analyze. Please fetch news first."
    return analyze_with_gemini(news_items)

def generate_pdf(news_items, date_str, language, search_keyword=None, analysis_text=None):
    """Generate a PDF report of news items with optional AI analysis"""
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
    
    ai_warning_style = ParagraphStyle(
        'AIWarningStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.orange,
        spaceAfter=8,
        leftIndent=10,
        borderWidth=0,
        borderColor=colors.orange,
        borderPadding=0,
        borderRadius=0,
        borderLeftWidth=2,
        borderLeftColor=colors.orange,
        borderLeftPadding=5
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
        
        # Highlight predefined abusive keywords
        for word in ABUSIVE_KEYWORDS:
            if re.search(r'\b' + word + r'\b', title, re.IGNORECASE):
                title = re.sub(r'\b' + word + r'\b', f'<font color="red"><b>{word}</b></font>', title, flags=re.IGNORECASE)
        
        # Highlight search keyword if provided
        if search_keyword and search_keyword.lower() in title.lower():
            title = re.sub(r'\b' + re.escape(search_keyword) + r'\b', f'<font color="green"><b>{search_keyword}</b></font>', title, flags=re.IGNORECASE)
        
        # Add the news item
        content.append(Paragraph(f"{i}. {title}", news_style))
        
        # Add AI-detected abusive elements warning if any
        if news.get("has_abusive") and news.get("abusive_elements"):
            ai_warning = f"⚠️ AI detected potentially problematic content: {', '.join(news.get('abusive_elements', []))}"
            content.append(Paragraph(ai_warning, ai_warning_style))
        
        # Add publication date if available
        if news.get("pub_date"):
            date_str = news["pub_date"].strftime("%Y-%m-%d %H:%M")
            content.append(Paragraph(f"Published: {date_str}", source_style))
            
        content.append(Paragraph(f"Source: {news['source']}", source_style))
        content.append(Paragraph(f"<a href='{news['link']}'>Read full article</a>", link_style))
        content.append(Spacer(1, 10))
    
    # Add AI Analysis if available
    if analysis_text:
        content.append(Spacer(1, 0.3*72))
        analysis_title_style = ParagraphStyle('AnalysisTitleStyle', parent=styles['h2'], fontSize=14, spaceAfter=10, textColor=colors.darkgreen)
        analysis_body_style = ParagraphStyle('AnalysisBodyStyle', parent=styles['Normal'], fontSize=10, leading=13, spaceAfter=8, leftIndent=10, rightIndent=10, alignment=4)
        content.append(Paragraph("Gemini AI Analysis", analysis_title_style))
        content.append(Spacer(1, 0.1*72))
        analysis_paragraphs = analysis_text.split('\n')
        for para in analysis_paragraphs:
            para_strip = para.strip()
            if para_strip:
                safe_para = para_strip.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                safe_para = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe_para)
                safe_para = re.sub(r'\*(.*?)\*', r'<i>\1</i>', safe_para)
                safe_para = safe_para.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>').replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')
                content.append(Paragraph(safe_para, analysis_body_style))

    # Build the PDF
    doc.build(content)
    buffer.seek(0)
    return buffer

def find_duplicate_news(news_items, threshold=0.8):
    """Find duplicate news items based on title similarity."""
    titles = [news['title'] for news in news_items]
    vectorizer = TfidfVectorizer().fit_transform(titles)
    vectors = vectorizer.toarray()
    csim = cosine_similarity(vectors)
    
    duplicates = {}
    for i in range(len(csim)):
        for j in range(i + 1, len(csim)):
            if csim[i][j] > threshold:
                if i not in duplicates:
                    duplicates[i] = []
                duplicates[i].append(j)
    
    return duplicates

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
    
    # AI analysis toggle
    use_ai_analysis = st.checkbox("Use AI to detect abusive content", value=False, 
                                 help="Enable AI-based detection of problematic content beyond predefined keywords")

st.write("##")

# Action buttons
col1, col2, col3, col4 = st.columns(4)
scrap_btn = col1.button("Scrap News")
analyze_btn = col2.button("Analyze with Gemini", disabled=not gemini_initialized)
generate_pdf_btn = col3.button("Generate PDF Report")
show_stats_btn = col4.button("Show News Coverage Statistics")

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
        .abuse-warning {
            color: orange;
            font-size: 0.8em;
            margin-top: 5px;
            padding: 3px;
            border-left: 3px solid orange;
        }
        .analysis-box {
            padding: 15px;
            border: 1px solid #4CAF50;
            border-radius: 5px;
            background-color: #f8f9fa;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        .analysis-title {
            color: #4CAF50;
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
        }
    </style>
"""
st.markdown(box_style, unsafe_allow_html=True)

# Initialize session state for news
if 'news_items' not in st.session_state:
    st.session_state.news_items = []
if 'analysis_text' not in st.session_state:
    st.session_state.analysis_text = None

# Scrape news when button is clicked
if scrap_btn:
    with st.spinner("Fetching news from multiple sources..."):
        # Get news from RSS feeds
        rss_news = fetch_rss_news(language_code, days_back, search_keyword, use_ai_analysis)
        
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
                    
                    # Check for abusive content using predefined keywords
                    has_keyword_abuse = any(re.search(r'\b' + word + r'\b', news_title, re.IGNORECASE) for word in ABUSIVE_KEYWORDS)
                    
                    # Check for abusive content using AI (if enabled)
                    ai_abuse_detected = False
                    ai_abuse_elements = []
                    
                    # Only use AI analysis if enabled and keyword detection didn't find anything
                    if use_ai_analysis and not has_keyword_abuse and gemini_initialized:
                        ai_abuse_detected, ai_abuse_elements = analyze_content_for_abuse(news_title)
                    
                    sarkari_news.append({
                        "title": news_title,
                        "link": href_link,
                        "description": "",
                        "source": "Sarkari Pariksha",
                        "hash": news_hash,
                        "has_abusive": has_keyword_abuse or ai_abuse_detected,
                        "abusive_elements": ai_abuse_elements,
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

# Analyze news when button is clicked
if analyze_btn:
    if not st.session_state.news_items:
        st.warning("No news fetched to analyze.", icon="⚠️")
    elif not gemini_initialized:
        st.error("Gemini API key missing/invalid.", icon="🔥")
    else:
        with st.spinner("Analyzing news with Google Gemini..."):
            st.session_state.analysis_text = analyze_news(st.session_state.news_items)

# Display news items
if st.session_state.news_items:
    for i, news in enumerate(st.session_state.news_items, 1):
        #title = highlight_abusive_words(news["title"], news.get("abusive_elements", []))
        title = highlight_abusive_words(news["title"], language_code, news.get("abusive_elements", []))
        if search_keyword:
            title = highlight_search_keyword(title, search_keyword)
        
        date_str = ""
        if news.get("pub_date"):
            date_str = f"<div class='news-date'>Published: {news['pub_date'].strftime('%Y-%m-%d %H:%M')}</div>"
        
        # Add an abuse warning if detected by AI
        abuse_warning = ""
        if news.get("has_abusive") and news.get("abusive_elements"):
            abuse_warning = f"""<div class="abuse-warning">
                ⚠️ AI detected potentially problematic content: {', '.join(news.get('abusive_elements', []))}
            </div>"""
        
        st.markdown(
            f"""<div class="custom-box">
                {i}- <a href="{news['link']}">{title}</a>
                {date_str}
                {abuse_warning}
                <div class="news-source">Source: {news['source']}</div>
            </div>""",
            unsafe_allow_html=True,
        )

# Display AI Analysis
if st.session_state.analysis_text:
    st.markdown("---")
    analysis_html = st.session_state.analysis_text.replace('```', '').replace('\n', '<br>')
    st.markdown(f"""<div class="analysis-box"><div class="analysis-title">✨ Gemini AI Analysis</div>{analysis_html}</div>""", unsafe_allow_html=True)
    st.markdown("---")

# Generate PDF report
if generate_pdf_btn and st.session_state.news_items:
    with st.spinner("Generating PDF report..."):
        pdf_buffer = generate_pdf(
            st.session_state.news_items, 
            date_display, 
            language_code, 
            search_keyword, 
            st.session_state.get('analysis_text')
        )
        
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

# Show news coverage statistics
if show_stats_btn:
    if not st.session_state.news_items:
        st.warning("No news fetched to analyze.", icon="⚠️")
    else:
        with st.spinner("Analyzing news coverage statistics..."):
            duplicates = find_duplicate_news(st.session_state.news_items)
            
            # Count sources
            source_counts = {}
            for item in st.session_state.news_items:
                source = item['source']
                source_counts[source] = source_counts.get(source, 0) + 1
            
            # Count abusive content
            abusive_count = sum(1 for item in st.session_state.news_items if item.get('has_abusive'))
            ai_detected_count = sum(1 for item in st.session_state.news_items if item.get('abusive_elements'))
            
            # Display statistics
            st.write("### News Coverage Statistics")
            
            # Source distribution
            st.write("#### Source Distribution")
            for source, count in source_counts.items():
                st.write(f"- **{source}**: {count} articles")
            
            # Content analysis
            st.write("#### Content Analysis")
            st.write(f"- **Total articles**: {len(st.session_state.news_items)}")
            st.write(f"- **Articles with sensitive content**: {abusive_count} ({abusive_count/len(st.session_state.news_items)*100:.1f}%)")
            if use_ai_analysis:
                st.write(f"- **Articles with AI-detected problematic content**: {ai_detected_count} ({ai_detected_count/len(st.session_state.news_items)*100:.1f}%)")
            
            # Similar coverage
            if duplicates:
                st.write("#### Similar Coverage Across Sources")
                for idx, dup_indices in duplicates.items():
                    st.write(f"**News Title:** {st.session_state.news_items[idx]['title']}")
                    st.write("**Covered by:**")
                    st.write(f"- {st.session_state.news_items[idx]['source']}")
                    for dup_idx in dup_indices:
                        st.write(f"- {st.session_state.news_items[dup_idx]['source']}")
                    st.write("---")
            else:
                st.write("No duplicate news items found across sources.")

# Add a section for topic modeling if there are enough news items
if len(st.session_state.news_items) >= 5 and gemini_initialized:
    st.write("### Want to see topic clusters?")
    if st.button("Generate Topic Clusters"):
        with st.spinner("Analyzing topics in news articles..."):
            # Prepare text for topic modeling
            all_text = [f"{item['title']} {item.get('description', '')}" for item in st.session_state.news_items]
            
            # Use Gemini to identify topics
            try:
                prompt = f"""Analyze the following news articles and identify 3-5 main topic clusters. 
                For each cluster, provide:
                1. A short descriptive name for the topic
                2. The key themes or focus of this topic cluster
                
                News articles to analyze:
                {all_text[:20]}  # Limit to 20 articles to avoid token limits
                
                Format your response as:
                Topic 1: [Name]
                - Key themes: [themes]
                - Related keywords: [keywords]
                
                Topic 2: [Name]
                ...and so on.
                """
                
                model = GenerativeModel('gemini-1.5-flash-latest')
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=800, temperature=0.4),
                    request_options={'timeout': 60}
                )
                
                topic_analysis = "".join(part.text for part in response.candidates[0].content.parts).strip()
                
                # Display the topics
                st.markdown("#### Topic Clusters in Current News")
                st.markdown(topic_analysis)
                
            except Exception as e:
                st.error(f"Error generating topic clusters: {str(e)}")

# Add a section for sentiment analysis
if st.session_state.news_items and gemini_initialized:
    st.write("### Analyze Sentiment of News Coverage")
    if st.button("Analyze Sentiment"):
        with st.spinner("Analyzing sentiment in news articles..."):
            # Prepare text for sentiment analysis
            titles = [item['title'] for item in st.session_state.news_items[:15]]  # Limit to 15 articles
            
            # Use Gemini for sentiment analysis
            try:
                prompt = f"""Analyze the sentiment of the following news headlines. 
                Provide an overall assessment of whether the news coverage is predominantly:
                - Positive
                - Negative
                - Neutral
                - Mixed
                
                Also identify any emotional tones present (fear, hope, anger, etc.) and explain your reasoning.
                
                News headlines:
                {titles}
                """
                
                model = GenerativeModel('gemini-1.5-flash-latest')
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=500, temperature=0.2),
                    request_options={'timeout': 45}
                )
                
                sentiment_analysis = "".join(part.text for part in response.candidates[0].content.parts).strip()
                
                # Display the sentiment analysis
                st.markdown("#### Sentiment Analysis of News Coverage")
                st.markdown(sentiment_analysis)
                
            except Exception as e:
                st.error(f"Error analyzing sentiment: {str(e)}")

# Add a section for content recommendations
if st.session_state.news_items:
    st.write("### News Recommendations")
    if st.button("Get Personalized Recommendations"):
        # Let user select interests
        interests = st.multiselect(
            "Select your interests:",
            ["Politics", "Technology", "Business", "Health", "Sports", "Entertainment", "Science", "Environment"]
        )
        
        if interests:
            with st.spinner("Generating personalized recommendations..."):
                # Filter news based on interests
                recommended_news = []
                
                if gemini_initialized:
                    # Use Gemini to match news to interests
                    try:
                        news_texts = [f"Title: {item['title']}\nDescription: {item.get('description', '')}" 
                                     for item in st.session_state.news_items[:20]]
                        
                        prompt = f"""Given the following news articles and user interests, identify which articles 
                        would be most relevant to the user's interests. Return the index numbers (starting from 0) 
                        of the most relevant articles.
                        
                        User interests: {', '.join(interests)}
                        
                        News articles:
                        {news_texts}
                        
                        Return only the indices of relevant articles as a comma-separated list, like: 0, 3, 5, 7
                        """
                        
                        model = GenerativeModel('gemini-1.5-flash-latest')
                        response = model.generate_content(
                            prompt,
                            generation_config=genai.types.GenerationConfig(
                                max_output_tokens=100, temperature=0.1),
                            request_options={'timeout': 30}
                        )
                        
                        indices_text = "".join(part.text for part in response.candidates[0].content.parts).strip()
                        
                        # Parse indices
                        try:
                            indices = [int(idx.strip()) for idx in indices_text.split(',') if idx.strip().isdigit()]
                            for idx in indices:
                                if 0 <= idx < len(st.session_state.news_items):
                                    recommended_news.append(st.session_state.news_items[idx])
                        except:
                            # Fallback if parsing fails
                            recommended_news = st.session_state.news_items[:5]
                            
                    except Exception as e:
                        st.error(f"Error generating recommendations: {str(e)}")
                        recommended_news = st.session_state.news_items[:5]
                else:
                    # Simple fallback if Gemini is not available
                    recommended_news = st.session_state.news_items[:5]
                
                # Display recommendations
                st.markdown("#### Recommended Articles Based on Your Interests")
                for i, news in enumerate(recommended_news, 1):
                    title = highlight_abusive_words(news["title"], news.get("abusive_elements", []))
                    st.markdown(
                        f"""<div class="custom-box recommendation">
                            {i}- <a href="{news['link']}">{title}</a>
                            <div class="news-source">Source: {news['source']}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

# Add a footer with information about the app
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 10px;">
    <p>Advanced News Scraper | Developed with Streamlit and Gemini AI</p>
    <p>This tool uses AI to analyze news content. AI-detected problematic content is highlighted in orange.</p>
</div>
""", unsafe_allow_html=True)

# Add a help section
with st.expander("Help & Information"):
    st.markdown("""
    ### How to use this app
    
    1. **Select Date Range**: Choose between today's news, this week's news, or a custom date.
    2. **Select Language**: Choose English, Hindi, or Kannada.
    3. **Search Keywords**: Optionally enter specific keywords to filter news.
    4. **AI Analysis**: Toggle AI-based detection of problematic content.
    5. **Actions**:
       - **Scrap News**: Fetch news from multiple sources
       - **Analyze with Gemini**: Get AI analysis of news trends and patterns
       - **Generate PDF Report**: Create a downloadable PDF report
       - **Show Statistics**: View news coverage statistics
    
    ### About AI Detection
    
    This app uses two methods to detect potentially problematic content:
    
    1. **Keyword-based detection**: Highlights predefined sensitive words in red
    2. **AI-based detection**: Uses Gemini AI to identify subtle forms of problematic content, highlighted in orange
    
    ### Privacy & Data Usage
    
    - This app does not store any user data
    - News content is processed in memory and not saved
    - API calls to Gemini are subject to Google's privacy policy
    """)