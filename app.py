import os
import time
import json
import feedparser
import requests
import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from newspaper import Article
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file, Response
from transformers import pipeline, AutoModelForSeq2SeqLM, AutoTokenizer
from fpdf import FPDF
import threading
import re
from collections import Counter
from googletrans import Translator
from gtts import gTTS
import tempfile
from bs4 import BeautifulSoup
import uuid
#import multiprocessing
#multiprocessing.set_start_method("fork", force=True)


# Download necessary NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Global variables
NEWS_CACHE = []
KEYWORD_STATS = {}
LAST_UPDATE = 0
UPDATE_INTERVAL = 900  # 15 minutes
AUDIO_CACHE = {}

# Initialize NLP pipelines
try:
    summarizer = pipeline("summarization", model="philschmid/bart-large-cnn-samsum", device=-1)
    sentiment_analyzer = pipeline("sentiment-analysis")
    
    # Initialize translation model for Kannada
    translator = Translator()
    
    # For more accurate Kannada-English translations, you can use a dedicated model
    try:
        kannada_model_name = "Helsinki-NLP/opus-mt-kn-en"  # Kannada to English
        english_model_name = "Helsinki-NLP/opus-mt-en-kn"  # English to Kannada
        
        kannada_to_english_model = AutoModelForSeq2SeqLM.from_pretrained(kannada_model_name)
        kannada_to_english_tokenizer = AutoTokenizer.from_pretrained(kannada_model_name)
        
        english_to_kannada_model = AutoModelForSeq2SeqLM.from_pretrained(english_model_name)
        english_to_kannada_tokenizer = AutoTokenizer.from_pretrained(english_model_name)
        
        specialized_translation_available = True
    except:
        print("Warning: Specialized Kannada translation models couldn't be loaded. Using Google Translate fallback.")
        specialized_translation_available = False
        
except Exception as e:
    print(f"Warning: Hugging Face transformers models couldn't be loaded: {str(e)}. Using fallback methods.")
    summarizer = None
    sentiment_analyzer = None
    translator = Translator()
    specialized_translation_available = False

# News sources (including Kannada sources)
NEWS_SOURCES = [
    {"name": "CNN", "rss": "http://rss.cnn.com/rss/cnn_topstories.rss", "language": "en"},
    {"name": "BBC", "rss": "http://feeds.bbci.co.uk/news/rss.xml", "language": "en"},
    {"name": "Reuters", "rss": "http://feeds.reuters.com/reuters/topNews", "language": "en"},
    {"name": "NPR", "rss": "https://feeds.npr.org/1001/rss.xml", "language": "en"},
    {"name": "The Guardian", "rss": "https://www.theguardian.com/world/rss", "language": "en"},
    # Kannada sources
    {"name": "Vijaya Karnataka", "rss": "https://vijaykarnataka.com/rss", "language": "kn"},
    {"name": "Prajavani", "rss": "https://www.prajavani.net/feed", "language": "kn"},
    {"name": "Udayavani", "rss": "https://www.udayavani.com/feed", "language": "kn"},
    # Add more sources as needed
]

# Function to translate text between languages
def translate_text(text, source_lang, target_lang):
    if not text:
        return ""
    
    # If specialized models are available for Kannada-English translation
    if specialized_translation_available and ((source_lang == 'kn' and target_lang == 'en') or 
                                             (source_lang == 'en' and target_lang == 'kn')):
        try:
            if source_lang == 'kn' and target_lang == 'en':
                inputs = kannada_to_english_tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
                outputs = kannada_to_english_model.generate(**inputs)
                translation = kannada_to_english_tokenizer.decode(outputs[0], skip_special_tokens=True)
            else:
                inputs = english_to_kannada_tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
                outputs = english_to_kannada_model.generate(**inputs)
                translation = english_to_kannada_tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translation
        except Exception as e:
            print(f"Error in specialized translation: {str(e)}. Falling back to Google Translate.")
    
    # Fallback to Google Translate
    try:
        translation = translator.translate(text, src=source_lang, dest=target_lang)
        return translation.text
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return text  # Return original text if translation fails

# Generate voice for headline
def generate_voice(text, lang='en'):
    try:
        # Create a temporary file for the audio
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_filename = temp_file.name
        temp_file.close()
        
        # Generate the audio file
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(temp_filename)
        
        return temp_filename
    except Exception as e:
        print(f"Error generating voice: {str(e)}")
        return None

# Simple fallback summarizer if transformers fails
def simple_summarize(text, max_length=150):
    sentences = text.split('.')
    if len(sentences) <= 3:
        return text
    
    # Take first 3 sentences as summary
    summary = '. '.join(sentences[:3]) + '.'
    return summary

# Simple fallback sentiment analyzer
def simple_sentiment(text):
    positive_words = ['good', 'great', 'excellent', 'positive', 'happy', 'success', 'benefit']
    negative_words = ['bad', 'terrible', 'negative', 'sad', 'failure', 'problem', 'crisis']
    
    words = word_tokenize(text.lower())
    pos_count = sum(1 for word in words if word in positive_words)
    neg_count = sum(1 for word in words if word in negative_words)
    
    if pos_count > neg_count:
        return {"label": "POSITIVE", "score": 0.7}
    elif neg_count > pos_count:
        return {"label": "NEGATIVE", "score": 0.7}
    else:
        return {"label": "NEUTRAL", "score": 0.9}

# Collect news from RSS feeds
def collect_news():
    articles = []
    
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source["rss"])
            for entry in feed.entries[:5]:  # Limit to 5 articles per source
                try:
                    # Extract full article using newspaper3k
                    article = Article(entry.link)
                    article.download()
                    article.parse()
                    
                    # Skip articles with very little content
                    if len(article.text) < 100:
                        continue
                    
                    # Get publish date
                    try:
                        published = entry.published
                    except:
                        published = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
                    
                    # Determine language
                    language = source.get("language", "en")
                    
                    # Create article object
                    article_obj = {
                        "id": str(uuid.uuid4()),
                        "title": article.title,
                        "text": article.text,
                        "source": source["name"],
                        "url": entry.link,
                        "published": published,
                        "image": article.top_image if hasattr(article, 'top_image') else "",
                        "language": language
                    }
                    
                    # Add translation if not in English
                    if language != "en":
                        article_obj["title_english"] = translate_text(article.title, language, "en")
                        article_obj["text_english"] = translate_text(article.text[:1000], language, "en")  # Limit translation to first 1000 chars
                    
                    # Add translation if not in Kannada (for demonstration of multi-language)
                    if language != "kn":
                        article_obj["title_kannada"] = translate_text(article.title, language, "kn")
                    
                    articles.append(article_obj)
                except Exception as e:
                    print(f"Error processing article from {source['name']}: {str(e)}")
        except Exception as e:
            print(f"Error fetching from {source['name']}: {str(e)}")
    
    return articles

# Analyze news with AI
def analyze_news(articles):
    for article in articles:
        # Determine which text to analyze (use English translation if available)
        text_to_analyze = article.get("text_english", article["text"]) if article["language"] != "en" else article["text"]
        
        # Generate summary
        if summarizer:
            try:
                # Truncate text if too long for the model
                text_for_summary = text_to_analyze[:1024]
                article["summary"] = summarizer(text_for_summary, max_length=100)[0]["summary_text"]
            except:
                article["summary"] = simple_summarize(text_to_analyze)
        else:
            article["summary"] = simple_summarize(text_to_analyze)
        
        # Analyze sentiment
        if sentiment_analyzer:
            try:
                article["sentiment"] = sentiment_analyzer(text_to_analyze[:512])[0]
            except:
                article["sentiment"] = simple_sentiment(text_to_analyze)
        else:
            article["sentiment"] = simple_sentiment(text_to_analyze)
        
        # Extract keywords
        try:
            stop_words = set(stopwords.words('english'))
            words = word_tokenize(text_to_analyze.lower())
            words = [word for word in words if word.isalnum() and word not in stop_words]
            word_freq = Counter(words)
            article["keywords"] = [word for word, count in word_freq.most_common(5)]
        except:
            article["keywords"] = []
        
        # Generate voice for headline
        try:
            # Use the appropriate language for TTS
            tts_lang = "en" if article["language"] not in ["kn", "hi", "ta", "te"] else "en"  # Fallback to English if language not supported by gTTS
            
            # Generate voice for the title (use English title for non-English articles for better pronunciation)
            title_for_voice = article.get("title_english", article["title"]) if article["language"] != "en" else article["title"]
            
            article["voice_url"] = f"/api/voice/{article['id']}"
            
            # Cache the text to be converted to speech
            AUDIO_CACHE[article["id"]] = {
                "text": title_for_voice,
                "lang": tts_lang,
                "file": None  # Will be generated on demand
            }
        except Exception as e:
            print(f"Error setting up voice: {str(e)}")
            article["voice_url"] = None
    
    return articles

# Get keyword statistics across all articles
def get_keyword_stats(articles, keyword):
    if not keyword:
        return {}
    
    keyword = keyword.lower()
    total_occurrences = 0
    articles_with_keyword = 0
    sources_with_keyword = set()
    language_distribution = {}
    
    for article in articles:
        # Check in the appropriate text field based on language
        if article["language"] == "en":
            text = article["text"].lower()
        else:
            text = article.get("text_english", article["text"]).lower()
        
        occurrences = text.count(keyword)
        
        if occurrences > 0:
            articles_with_keyword += 1
            sources_with_keyword.add(article["source"])
            total_occurrences += occurrences
            article["keyword_count"] = occurrences
            
            # Track language distribution
            lang = article["language"]
            language_distribution[lang] = language_distribution.get(lang, 0) + 1
        else:
            article["keyword_count"] = 0
    
    return {
        "keyword": keyword,
        "total_occurrences": total_occurrences,
        "articles_with_keyword": articles_with_keyword,
        "percentage_of_articles": round((articles_with_keyword / max(1, len(articles))) * 100, 2),
        "sources_with_keyword": len(sources_with_keyword),
        "total_sources": len(set(a["source"] for a in articles)),
        "language_distribution": language_distribution
    }

# Generate PDF with highlighted keywords
def generate_pdf(articles, keyword):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, 'Multi-language News Aggregator Report', 0, 1, 'C')
            self.ln(5)
        
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    pdf = PDF()
    pdf.add_page()
    
    # Add keyword stats
    stats = get_keyword_stats(articles, keyword)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f"Keyword Analysis: '{keyword}'", 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 10, f"Total occurrences: {stats.get('total_occurrences', 0)}", 0, 1)
    pdf.cell(0, 10, f"Articles containing keyword: {stats.get('articles_with_keyword', 0)} out of {len(articles)}", 0, 1)
    pdf.cell(0, 10, f"Percentage of articles: {stats.get('percentage_of_articles', 0)}%", 0, 1)
    pdf.cell(0, 10, f"Sources containing keyword: {stats.get('sources_with_keyword', 0)} out of {stats.get('total_sources', 0)}", 0, 1)
    
    # Add language distribution
    if stats.get('language_distribution'):
        pdf.ln(5)
        pdf.cell(0, 10, "Language Distribution:", 0, 1)
        for lang, count in stats.get('language_distribution', {}).items():
            lang_name = {"en": "English", "kn": "Kannada", "hi": "Hindi", "ta": "Tamil", "te": "Telugu"}.get(lang, lang)
            pdf.cell(0, 10, f"- {lang_name}: {count} articles", 0, 1)
    
    pdf.ln(10)
    
    # Add articles
    for article in articles:
        pdf.set_font('Arial', 'B', 12)
        
        # Add title in original language
        pdf.cell(0, 10, article["title"], 0, 1)
        
        # Add English translation for non-English articles
        if article["language"] != "en" and article.get("title_english"):
            pdf.set_font('Arial', 'I', 10)
            pdf.cell(0, 10, f"(English: {article['title_english']})", 0, 1)
        
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 10, f"Source: {article['source']} | Language: {article['language']} | Published: {article['published']}", 0, 1)
        
        pdf.set_font('Arial', '', 10)
        
        # Determine which text to use
        if article["language"] == "en":
            text = article["text"]
        else:
            # Use both original and English translation
            text = article.get("text_english", article["text"])
            pdf.multi_cell(0, 5, f"Original language content available in the source: {article['url']}", 0)
        
        # Highlight keyword in text
        if keyword:
            # Split text by keyword to highlight
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            parts = pattern.split(text)
            
            for i, part in enumerate(parts):
                pdf.set_text_color(0, 0, 0)  # Black text
                pdf.multi_cell(0, 5, part, 0)
                
                # Add highlighted keyword between parts (except after the last part)
                if i < len(parts) - 1:
                    pdf.set_text_color(255, 0, 0)  # Red text for keyword
                    pdf.multi_cell(0, 5, keyword, 0)
        else:
            pdf.multi_cell(0, 5, text, 0)
        
        pdf.ln(5)
        
        # Add AI analysis
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 10, "AI Analysis:", 0, 1)
        
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 5, f"Summary: {article['summary']}", 0)
        pdf.multi_cell(0, 5, f"Sentiment: {article['sentiment']['label']} ({round(article['sentiment']['score'] * 100)}%)", 0)
        
        if article.get("keyword_count", 0) > 0:
            pdf.multi_cell(0, 5, f"Keyword '{keyword}' appears {article['keyword_count']} times", 0)
        
        pdf.ln(10)
    
    # Save PDF
    filename = f"news_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

# Background news update function
def update_news_background():
    global NEWS_CACHE, LAST_UPDATE, KEYWORD_STATS
    
    while True:
        current_time = time.time()
        if current_time - LAST_UPDATE > UPDATE_INTERVAL:
            print("Updating news...")
            try:
                articles = collect_news()
                analyzed_articles = analyze_news(articles)
                NEWS_CACHE = analyzed_articles
                LAST_UPDATE = current_time
                print(f"News updated: {len(NEWS_CACHE)} articles")
            except Exception as e:
                print(f"Error updating news: {str(e)}")
        
        time.sleep(60)  # Check every minute

# Start background thread for news updates
news_thread = threading.Thread(target=update_news_background, daemon=True)
news_thread.start()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/news')
def get_news():
    keyword = request.args.get('keyword', '').strip()
    language = request.args.get('language', 'all')
    
    # Force update if cache is empty
    if not NEWS_CACHE:
        global LAST_UPDATE
        articles = collect_news()
        analyzed_articles = analyze_news(articles)
        NEWS_CACHE.extend(analyzed_articles)
        LAST_UPDATE = time.time()
    
    # Filter by language if specified
    filtered_articles = NEWS_CACHE
    if language != 'all':
        filtered_articles = [a for a in NEWS_CACHE if a['language'] == language]
    
    # Get keyword stats if keyword provided
    if keyword:
        stats = get_keyword_stats(filtered_articles, keyword)
        return jsonify({
            "articles": filtered_articles,
            "stats": stats,
            "last_updated": datetime.fromtimestamp(LAST_UPDATE).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({
        "articles": filtered_articles,
        "last_updated": datetime.fromtimestamp(LAST_UPDATE).strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/pdf')
def download_pdf():
    keyword = request.args.get('keyword', '').strip()
    
    try:
        filename = generate_pdf(NEWS_CACHE, keyword)
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/voice/<article_id>')
def get_voice(article_id):
    if article_id not in AUDIO_CACHE:
        return jsonify({"error": "Article not found"}), 404
    
    audio_info = AUDIO_CACHE[article_id]
    
    # Generate the audio file if it doesn't exist yet
    if not audio_info["file"] or not os.path.exists(audio_info["file"]):
        audio_info["file"] = generate_voice(audio_info["text"], audio_info["lang"])
    
    if not audio_info["file"]:
        return jsonify({"error": "Failed to generate audio"}), 500
    
    # Return the audio file
    return send_file(audio_info["file"], mimetype="audio/mp35")

@app.route('/api/languages')
def get_languages():
    # Get all available languages in the current news cache
    languages = list(set(article["language"] for article in NEWS_CACHE))
    
    language_names = {
        "en": "English",
        "kn": "Kannada",
        "hi": "Hindi",
        "ta": "Tamil",
        "te": "Telugu"
    }
    
    language_info = [{"code": lang, "name": language_names.get(lang, lang)} for lang in languages]
    
    return jsonify(language_info)

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('temp', exist_ok=True)
    
    # Make sure we have initial news data
    if not NEWS_CACHE:
        try:
            articles = collect_news()
            NEWS_CACHE = analyze_news(articles)
            LAST_UPDATE = time.time()
            print(f"Initial news loaded: {len(NEWS_CACHE)} articles")
        except Exception as e:
            print(f"Error loading initial news: {str(e)}")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5004, debug=True)