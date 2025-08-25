# currency.py
import requests
import os

# --- Configuration for ExchangeRate-API ---
EXCHANGERATE_API_KEY = os.environ.get("EXCHANGERATE_API_KEY")
EXCHANGERATE_URL = f"https://v6.exchangerate-api.com/v6/{EXCHANGERATE_API_KEY}/pair"

# A simple mapping for user-friendly input
CURRENCY_MAP = {
    "vietnam": "VND",
    "india": "INR",
    "dollar": "USD",
    "usd": "USD",
    "euro": "EUR",
    "eur": "EUR",
    "yen": "JPY",
    "jpy": "JPY",
    "pound": "GBP",
    "gbp": "GBP",
    "canadian dollar": "CAD",
    "cad": "CAD",
    "australian dollar": "AUD",
    "aud": "AUD"
}

def convert_currency(amount_str, from_currency, to_currency):
    """
    Converts an amount from one currency to another using the ExchangeRate-API.
    """
    if not EXCHANGERATE_API_KEY:
        return "❌ The ExchangeRate-API key is not configured. This feature is disabled."
    
    try:
        # Pre-process currency strings to handle user-friendly input
        from_curr = CURRENCY_MAP.get(from_currency.lower(), from_currency.upper())
        to_curr = CURRENCY_MAP.get(to_currency.lower(), to_currency.upper())
        amount = float(amount_str)

        if from_curr == to_curr:
            return f"✅ {amount} {from_curr} is equal to {amount} {to_curr}."
            
        url = f"{EXCHANGERATE_URL}/{from_curr}/{to_curr}/{amount}"
        
        response = requests.get(url)
        response.raise_for_status() # Raise an error for bad status codes
        
        data = response.json()
        
        if data.get("result") != "success":
             error_type = data.get("error-type", "Unknown error")
             return f"⚠️ Currency conversion failed: {error_type}. Please check your currency codes."

        converted_amount = data["conversion_result"]
        
        return f"✅ *{amount:,} {from_curr}* is equal to *{converted_amount:,.2f} {to_curr}*"

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error during currency conversion: {e.response.text}")
        return "❌ Sorry, the currency service is currently unavailable. Please check your API key and try again."
    except (ValueError, KeyError) as e:
        print(f"Data parsing error in currency conversion: {e}")
        return "❌ I couldn't understand that. Please use the format: `<amount> <from_currency> to <to_currency>`."
    except Exception as e:
        print(f"Currency conversion error: {e}")
        return "❌ An unexpected error occurred."
