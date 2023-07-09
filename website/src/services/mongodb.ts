import { MongoClient } from "mongodb";

const uri = process.env.MONGODB_URI!;

let client: MongoClient;
let connection: MongoClient;

async function connectDB() {
  if (connection) return connection.db("prisfinder");

  client = new MongoClient(uri);
  connection = await client.connect();

  return connection.db("prisfinder");
}

export default connectDB;
