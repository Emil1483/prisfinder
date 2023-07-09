import { NextApiRequest, NextApiResponse } from "next";
import { ObjectId } from "mongodb";
import connectDB from "@/services/mongodb";

import * as crypto from "crypto";

function objectIdFromString(string: string): ObjectId {
  const stringBytes = Buffer.from(string, "utf8");
  const hexdigest = crypto
    .createHash("sha256")
    .update(stringBytes)
    .digest("hex");

  return new ObjectId(hexdigest.slice(0, 24));
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method === "PATCH") {
    try {
      const { id } = req.query;

      const db = await connectDB();
      const products_collection = db.collection("products");
      const urls_collection = db.collection("urls");

      const { finn_query } = req.body;

      if (typeof finn_query != "string") {
        return res
          .status(400)
          .json({ success: false, message: "finn_query must be a string" });
      }
      if (finn_query.trim().length == 0) {
        return res
          .status(400)
          .json({ success: false, message: "finn_query must not be empty" });
      }

      const result = await products_collection.updateOne(
        { _id: new ObjectId(id as string) },
        { $set: req.body }
      );

      if (result.matchedCount === 1) {
        await urls_collection.updateOne(
          {
            _id: objectIdFromString(id as string),
          },
          {
            $set: {
              domain: "finn.no",
              url: id as string,
            },
          },
          {
            upsert: true,
          }
        );
        res.status(200).json({ success: true });
      } else {
        res.status(404).json({ success: false, message: "Product not found" });
      }
    } catch (error) {
      console.error("Failed to update query", error);
      res
        .status(500)
        .json({ success: false, message: "Failed to update query " + error });
    }
  } else {
    res.status(405).json({ success: false, message: "Method Not Allowed" });
  }
}
