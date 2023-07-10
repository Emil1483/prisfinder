import { GetServerSideProps } from 'next';
import { ObjectId } from 'mongodb';
import { ParsedUrlQuery } from 'querystring';
import { Product } from '@/models/product';
import { useState } from 'react';
import { FinnAd } from '@/models/finnAd';

import connectDB from '@/services/mongodb';
import styles from './styles.module.css'
import FinnAds from '@/pages/products/finnAds/finnAds';


const ProductDetails = ({ product, finnAds }: { product: Product, finnAds: FinnAd[] }) => {
    const [query, setQuery] = useState(product.finn_query);

    const handleQueryChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setQuery(event.target.value);
    };

    const handleUpdateQuery = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        try {
            const response = await fetch(`/api/products/${product._id}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ finn_query: query }),
            });

            if (response.ok) {
                product.finn_query = query;
                alert('Successfully set query')
            } else {
                alert('Failed to update query ' + await response.text());
            }
        } catch (error) {
            alert('Failed to update query ' + error);
        }
    };

    return (
        <div className={styles.product_details}>
            <h1>{product.name}</h1>
            <div className={styles.product_image}>
                <img src={product.image} alt={product.name} />
            </div>
            <div className={styles.product_info}>
                <form onSubmit={handleUpdateQuery}>
                    <label htmlFor="finnQuery">Finn Query: </label>
                    <input
                        type="text"
                        id="finnQuery"
                        value={query}
                        onChange={handleQueryChange}
                    />
                    <button type="submit">
                        Set
                    </button>
                </form>
                <h2>Description:</h2>
                <p>{product.description}</p>
                <h2>Brand:</h2>
                <p>{product.brand}</p>
                <h2>MPNs:</h2>
                <ul>
                    {product.mpns.map((mpn, index) => (
                        <li key={index}>{mpn}</li>
                    ))}
                </ul>
                <h2>GTINs:</h2>
                <ul>
                    {product.gtins.map((gtin, index) => (
                        <li key={index}>{gtin}</li>
                    ))}
                </ul>
                <h2>Retailers:</h2>
                <ul>
                    {product.retailers.map((retailer, index) => (
                        <li key={index}>
                            <h3>{retailer.name}</h3>
                            <p>Price: {retailer.price}</p>
                            <p>SKU: {retailer.sku}</p>
                            <p>URL: {retailer.url}</p>
                            <p>Category: {retailer.category}</p>
                        </li>
                    ))}
                </ul>
                <h2>Category:</h2>
                {product.category ? (
                    <p>
                        Main: {product.category.main}, Sub: {product.category.sub},{" "}
                        Product: {product.category.product}
                    </p>
                ) : (
                    <p>Category undefined</p>
                )}
            </div>
            <FinnAds finnAds={finnAds}></FinnAds>
        </div>
    );
};

export default ProductDetails;


interface Params extends ParsedUrlQuery {
    id: string;
}

export const getServerSideProps: GetServerSideProps<{ product: Product, finnAds: FinnAd[] }, Params> = async ({ params }) => {
    const { id } = params!;
    const db = await connectDB();
    const productsCollection = db.collection('products');
    const finnAdsCollection = db.collection('finn_ads');

    const product = await productsCollection.findOne({ _id: new ObjectId(id as string) });
    const finnAdsCursor = await finnAdsCollection.find({ product_id: new ObjectId(id as string) });

    const finnAds: FinnAd[] = []
    for await (const doc of finnAdsCursor) {
        finnAds.push(JSON.parse(JSON.stringify(doc)))
    }

    return {
        props: {
            product: JSON.parse(JSON.stringify(product)),
            finnAds: finnAds,
        },
    };
};