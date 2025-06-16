'use client';

import { useState, useEffect } from 'react';
import NewsCard from '@/components/NewsCard';
import SearchBar from '@/components/SearchBar';
import LanguageSelector from '@/components/LanguageSelector';
import DateSelector from '@/components/DateSelector';
import { NewsItem } from '@/types/news';

export default function Home() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState('en');
  const [searchQuery, setSearchQuery] = useState('');
  const [dateRange, setDateRange] = useState('today');
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [customDate, setCustomDate] = useState('');

  const fetchNews = async () => {
    setLoading(true);
    try {
      // TODO: Replace with your actual API endpoint
      const response = await fetch('/api/news', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          language,
          searchQuery,
          dateRange,
          customDate,
        }),
      });
      const data = await response.json();
      console.log('News API response:', data);
      if (Array.isArray(data)) {
        // in case the API directly returns an array (fallback)
        setNews(data as NewsItem[]);
      } else {
        setNews(Array.isArray(data.items) ? data.items : []);
        if (data.analysis) {
          setAnalysis(data.analysis as string);
        }
      }
    } catch (error) {
      console.error('Error fetching news:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNews();
  }, [language, dateRange]);

  return (
    <main className="min-h-screen bg-black text-white p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-5xl font-extrabold text-center mb-10">
          Advanced News Analyzer
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <LanguageSelector value={language} onChange={setLanguage} />
          <DateSelector value={dateRange} onChange={(val)=>{setDateRange(val); if(val!== 'custom'){setCustomDate('')}}} />
          <SearchBar value={searchQuery} onChange={setSearchQuery} onSearch={fetchNews} />
        </div>

        {dateRange === 'custom' && (
          <div className="mb-6">
            <label className="block text-sm text-gray-400 mb-2">Select custom date</label>
            <input
              type="date"
              value={customDate}
              onChange={(e) => setCustomDate(e.target.value)}
              className="bg-[#111] text-white border border-[#333] rounded-lg py-2 px-3 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
            />
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {news.length > 0 ? (
              news.map((item) => <NewsCard key={item.hash} news={item} />)
            ) : (
              <p className="text-gray-400 col-span-full text-center">No news found for selected criteria.</p>
            )}
          </div>
        )}

        {analysis && (
          <div className="mt-12 px-6 py-4 bg-gray-800 rounded-lg border border-blue-500/30">
            <h2 className="text-2xl font-semibold text-blue-400 mb-4">AI Analysis</h2>
            <p className="whitespace-pre-line text-gray-300 text-sm">{analysis}</p>
          </div>
        )}
      </div>
    </main>
  );
} 