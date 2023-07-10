import { FinnAd } from '@/models/finnAd';
import Link from 'next/link';
import React from 'react';

import styles from './finnAds.module.css'


const FinnAds = ({ finnAds = [] }: { finnAds: FinnAd[] }) => {
    return (
        <div className="finn-ad-list">
            <h2>Finn Ads</h2>
            {finnAds.map((finnAd) => (
                <Link key={finnAd._id}
                    href={`https://www.finn.no/bap/forsale/ad.html?finnkode=${finnAd.ad_id}`}
                    target="_blank"
                >
                    <div className={styles.finn_ad_item}>
                        <img src={finnAd.image.url} alt="Ad Image" className={styles.finn_ad_image} />
                        <div className={styles.finn_ad_content}>
                            <h2 className={styles.finn_ad_heading}>{finnAd.heading}</h2>
                            <p className={styles.finn_ad_price}>{`${finnAd.price.amount} ${finnAd.price.currency_code}`}</p>
                        </div>
                    </div>
                </Link>
            ))}
        </div>
    );
};

export default FinnAds;
