import os
import uuid
from dotenv import load_dotenv

import requests


def translate_to_eng(string: str) -> str:
    endpoint = "https://api.cognitive.microsofttranslator.com"
    location = os.getenv("AZURE_TRANSLATOR_LOCATION")
    key = os.getenv("AZURE_TRANSLATOR_KEY")

    path = "/translate"
    constructed_url = endpoint + path

    params = {"api-version": "3.0", "from": "no", "to": ["en"]}

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Ocp-Apim-Subscription-Region": location,
        "Content-type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4()),
    }

    body = [{"text": string}]

    response = requests.post(constructed_url, params=params, headers=headers, json=body)
    return response.json()[0]["translations"][0]["text"]


if __name__ == "__main__":
    load_dotenv()
    print(translate_to_eng("True wireless hodetelefoner"))
