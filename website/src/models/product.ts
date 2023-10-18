import {
  Product as PrismaProduct,
  Gtin,
  Mpn,
  ProductRetailer,
} from "@prisma/client";
import { JsonObject } from "@prisma/client/runtime/library";

export interface Product {
  id: number;
  name: string;
  finn_query: string | null;
  brand: string | null;
  description: string;
  image: string;
  mpns: string[];
  gtins: string[];
  retailers: Retailer[];
  category: Category | null;
}

export interface Category {
  main: number;
  sub: number;
  product: number;
}

export interface Retailer {
  name: string;
  price: number;
  sku: string;
  url: string;
  category: string;
}

export function fromPrismaProduct(
  p: PrismaProduct & {
    gtins: Gtin[];
    mpns: Mpn[];
    retailers: ProductRetailer[];
  }
) {
  return {
    id: p.id,
    name: p.name,
    finn_query: p.finn_query,
    brand: p.brand,
    description: p.description,
    gtins: p.gtins.map((g) => g.gtin),
    mpns: p.mpns.map((m) => m.mpn),
    image: p.image,
    retailers: p.retailers.map((r) => ({
      category: r.category,
      name: r.name,
      price: r.price,
      sku: r.sku,
      url: r.url,
    })),
    category: p.category
      ? {
          main: (p.category as JsonObject).main as number,
          sub: (p.category as JsonObject).sub as number,
          product: (p.category as JsonObject).product as number,
        }
      : null,
  };
}
