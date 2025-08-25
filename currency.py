# currency.py
import requests

def convert_currency(amount_str, from_currency, to_currency):
    """
    Converts an amount from one currency to another using the Frankfurter API.
    """
    try:
        amount = float(amount_str)
        from_curr = from_currency.upper()
        to_curr = to_currency.upper()

        if from_curr == to_curr:
            return f"✅ {amount} {from_curr} is equal to {amount} {to_curr}."

        url = f"https://api.frankfurter.app/latest?amount={amount}&from={from_curr}&to={to_curr}"
        
        response = requests.get(url)
        response.raise_for_status() # Raise an error for bad status codes
        
        data = response.json()
        
        if to_curr not in data["rates"]:
             return f"⚠️ The currency code '{to_curr}' is not supported by the service."

        converted_amount = data["rates"][to_curr]
        
        return f"✅ *{amount:,} {from_curr}* is equal to *{converted_amount:,.2f} {to_curr}*"

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error during currency conversion: {e.response.text}")
        if e.response.status_code == 422: # Unprocessable Entity (e.g., invalid currency code)
             return f"⚠️ Invalid currency code. Please use standard 3-letter codes like USD, INR, EUR."
        else:
            return "❌ Sorry, the currency service is currently unavailable."
    except (ValueError, KeyError) as e:
        print(f"Data parsing error in currency conversion: {e}")
        return "❌ I couldn't understand that. Please use the format: `<amount> <from_currency> to <to_currency>`."
    except Exception as e:
        print(f"Currency conversion error: {e}")
        return "❌ An unexpected error occurred."
