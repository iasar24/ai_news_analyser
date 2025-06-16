import { NewsItem } from '@/types/news';
import Image from 'next/image';
import { useState, useEffect } from 'react';

interface NewsCardProps {
  news: NewsItem;
}

export default function NewsCard({ news }: NewsCardProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    const fetchImage = async () => {
      try {
        // Using Unsplash API to get relevant images
        const response = await fetch(`/api/image-search?query=${encodeURIComponent(news.title)}`);
        const data = await response.json();
        if (data.url) {
          setImageUrl(data.url);
        }
      } catch (error) {
        console.error('Error fetching image:', error);
      }
    };

    fetchImage();
  }, [news.title]);

  return (
    <div className="bg-[#111] border border-[#333] rounded-lg overflow-hidden hover:border-accent transition-colors duration-200">
      {imageUrl && (
        <div className="relative h-48 w-full">
          <Image
            src={imageUrl}
            alt={news.title}
            fill
            className="object-cover"
          />
        </div>
      )}
      
      <div className="p-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-blue-400">{news.source}</span>
          <span className="text-xs text-gray-400">{new Date(news.pub_date).toLocaleDateString()}</span>
        </div>
        
        <h3 className="text-xl font-semibold mb-2 line-clamp-2">
          <a href={news.link} target="_blank" rel="noopener noreferrer" 
             className="hover:text-blue-400 transition-colors duration-200">
            {news.title}
          </a>
        </h3>
        
        {news.description && (
          <p className="text-gray-400 text-sm mb-4 line-clamp-3">
            {news.description}
          </p>
        )}

        {news.has_abusive && (
          <div className="mt-2 p-2 bg-red-900/20 border border-red-500/50 rounded-md">
            <p className="text-red-400 text-xs">
              ⚠️ This content may contain sensitive material
            </p>
            {news.abusive_elements.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1">
                {news.abusive_elements.map((element, index) => (
                  <span key={index} className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded">
                    {element}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
} 