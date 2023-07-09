import { GetServerSideProps } from 'next';
import { ObjectId } from 'mongodb';
import connectDB from '@/services/mongodb';
import { ParsedUrlQuery } from 'querystring';
import { Product } from '@/models/product';

import styles from './styles.module.css'


const ProductDetails = ({ product }: { product: Product }) => {
    return (
        <div className={styles.product_details}>
            <h1>{product.name}</h1>
            <div className={styles.product_image}>
                <img src={product.image} alt={product.name} />
            </div>
            <div className={styles.product_info}>
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
        </div>
    );
};

export default ProductDetails;


interface Params extends ParsedUrlQuery {
    id: string;
}

export const getServerSideProps: GetServerSideProps<{ product: Product }, Params> = async ({ params }) => {
    const { id } = params!;
    const db = await connectDB();
    const collection = db.collection('products');
    const product = await collection.findOne({ _id: new ObjectId(id as string) });

    return {
        props: {
            product: JSON.parse(JSON.stringify(product)),
        },
    };
};