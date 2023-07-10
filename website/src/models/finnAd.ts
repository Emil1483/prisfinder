export interface FinnAd {
  _id: string;
  ad_id: number;
  ad_type: number;
  coordinates: Coordinates;
  distance: number;
  extras: any[];
  flags: string[];
  heading: string;
  id: string;
  image_urls: string[];
  labels: any[];
  location: string;
  main_search_key: string;
  price: Price;
  timestamp: number;
  trade_type: string;
  type: string;
  product_id: string;
  image: Image | null;
}

export interface Coordinates {
  lat: number;
  lon: number;
}

export interface Image {
  url: string;
  path: string;
  height: number;
  width: number;
  aspect_ratio: number;
}

export interface Price {
  amount: number;
  currency_code: string;
}
