export interface NewsItem {
  title: string;
  link: string;
  description: string;
  source: string;
  hash: string;
  has_abusive: boolean;
  abusive_elements: string[];
  pub_date: string;
  image_url?: string;
}

export interface NewsApiResponse {
  items: NewsItem[];
  analysis?: string;
} 