import { Product } from "@/models/product";
import connectDB from "@/services/mongodb";
import Link from "next/link";

import styles from "./styles.module.css"

export async function getServerSideProps() {
    const db = await connectDB();
    const collection = db.collection('products');
    const products = await collection.aggregate([{ $sample: { size: 20 } }]).toArray();

    return {
        props: {
            products: JSON.parse(JSON.stringify(products)),
        },
    };
}

const Home = ({ products }: { products: Product[] }) => {
    return (
        <div className={styles.product_list}>
            {products.map((product) => (
                <Link key={product._id.toString()} href={`/products/${product._id.toString()}`}>
                    <div className={styles.product_card}>
                        <div className={styles.product_image}>
                            <img src={product.image} alt={product.name} />
                        </div>
                        <div className={styles.product_info}>
                            <h2>{product.name}</h2>
                            <p>Brand: {product.brand}</p>
                            <p>Description: {product.description}</p>
                        </div>
                    </div>
                </Link>
            ))}
        </div>
    );
};

export default Home;