import requests

def correct_grammar(text):
    url = "https://api.languagetool.org/v2/check"
    params = {
        "text": text,
        "language": "en-US"
    }

    try:
        response = requests.post(url, data=params)
        result = response.json()

        matches = result.get("matches", [])
        if not matches:
            return "✅ No grammar mistakes found."

        # Apply corrections to the original text
        corrected = list(text)
        offset = 0

        for match in matches:
            if match["replacements"]:
                start = match["offset"] + offset
                end = start + match["length"]
                replacement = match["replacements"][0]["value"]
                corrected[start:end] = replacement
                offset += len(replacement) - match["length"]

        final_text = "".join(corrected)
        return f"📝 Corrected: {final_text}"

    except Exception as e:
        return f"⚠️ LanguageTool API error: {str(e)}"
