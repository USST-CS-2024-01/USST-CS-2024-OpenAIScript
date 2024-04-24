import json
import re

import requests

function_define = {
    "type": "function",
    "function": {
        "name": "callback_score",
        "description": "Submits a score and a comment for a document, must be "
                       "called after the document has been reviewed.",
        "parameters": {
            "type": "object",
            "properties": {
                "score": {
                    "type": "integer",
                    "format": "int32",
                    "description": "Score of the document between 0 to 100.",
                    "minimum": 0,
                    "maximum": 100
                },
                "comment": {
                    "type": "string",
                    "maxLength": 1000,
                    "description": "Comment about the document, in Chinese."
                }
            },
            "required": ["score", "comment"]
        }
    }
}

DEFAULT_PROMPT = ("This GPT is designed to assess documents based on specific "
                  "criteria such as the document's standardization and content "
                  "accuracy. It will read documents, score them out of 100, and "
                  "provide a brief evaluation in about 200 Chinese characters. "
                  "The GPT should ignore formatting issues that may arise from"
                  " conversions from formats like Word. Here is an example of"
                  " a document content:")
DEFAULT_MODEL = "gpt-4-turbo"
DEFAULT_SECRET_KEY = "secret_key_here"
DEFAULT_ENDPOINT = "https://api.openai.com"


def evaluate_document(
        document: str,
        model: str,
        prompt: str,
        secret_key: str,
        endpoint: str
):
    """
    Evaluates a document based on specific criteria such as the document's
    standardization and content accuracy. It reads the document, scores it out
    of 100, and provides a brief evaluation in about 200 Chinese characters.

    :param document: The document to evaluate.
    :param model: The model to use for evaluation.
    :param prompt: The prompt to use for evaluation.
    :param secret_key: The secret key for the OpenAI API.
    :param endpoint: The endpoint for the OpenAI API.
    :return: The score and evaluation of the document.
    """
    if model is None:
        model = DEFAULT_MODEL
    if prompt is None:
        prompt = DEFAULT_PROMPT
    if secret_key is None:
        secret_key = DEFAULT_SECRET_KEY
    if endpoint is None:
        endpoint = DEFAULT_ENDPOINT

    document = re.sub(r"\s+", " ", document.strip())

    response = requests.post(
        f"{endpoint}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {secret_key}"
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": document}
            ],
            "tool_choice": {
                "type": "function",
                "function": {
                    "name": "callback_score",
                }
            },
            "tools": [function_define]
        }
    )
    if response.status_code != 200:
        raise Exception(f"Failed to evaluate document: {response.text}")

    resp = response.json()
    calls = resp["choices"][0]["message"]["tool_calls"]

    score, comment = None, None
    for call in calls:
        func = call.get("function")
        if func["name"] == "callback_score":
            args = json.loads(func["arguments"])
            score = args["score"]
            comment = args["comment"]
            break

    return score, comment
