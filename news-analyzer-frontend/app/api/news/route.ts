import { NextResponse } from 'next/server';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { language, searchQuery, dateRange, customDate } = body;

    // Convert frontend parameters to match Python backend expectations
    const params = new URLSearchParams({
      language_code: language,
      search_keyword: searchQuery || '',
      date_option: dateRange === 'week' ? 'Latest News (This Week)' : 
                   dateRange === 'today' ? 'Latest News (Today)' : 'Custom Date',
      ...(customDate ? (() => {
        const d = new Date(customDate);
        if (!isNaN(d.getTime())) {
          return {
            year: d.getFullYear().toString(),
            month: d.toLocaleString('default', { month: 'long' }).toLowerCase(),
            day: d.getDate().toString(),
          };
        }
        return {};
      })() : {}),
    });

    const response = await fetch(`${PYTHON_BACKEND_URL}/api/news?${params}`);
    const data = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching news:', error);
    return NextResponse.json(
      { error: 'Failed to fetch news' },
      { status: 500 }
    );
  }
} 