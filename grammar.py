import requests

def correct_grammar(text):
    url = "https://api.languagetoolplus.com/v2/check"
    data = {
        "text": text,
        "language": "en-US"
    }
    try:
        response = requests.post(url, data=data)
        matches = response.json().get("matches", [])
        if matches:
            correction = matches[0]["replacements"][0]["value"]
            return f"📝 Corrected: {correction}"
        else:
            return "✅ No grammar issues found."
    except:
        return "⚠️ Error checking grammar."
