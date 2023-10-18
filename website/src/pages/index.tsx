import { Product, fromPrismaProduct } from "@/models/product";
import Link from "next/link";

import styles from "./styles.module.css"
import prisma from "@/services/prisma";
import { JsonObject } from "@prisma/client/runtime/library";

export async function getServerSideProps() {
    const prismaProducts = await prisma.product.findMany({
        take: 10,
        include: {
            gtins: true,
            mpns: true,
            retailers: true,
        },
    })

    const products = prismaProducts.map(fromPrismaProduct);

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
                <Link key={product.id.toString()} href={`/products/${product.id.toString()}`}>
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