import os
from dotenv import load_dotenv
from twilio.rest import Client
from utils.location import get_location

# Load .env properly
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

ACCOUNT_SID = os.getenv("TWILIO_SID")
AUTH_TOKEN = os.getenv("TWILIO_TOKEN")

FROM_WHATSAPP = "whatsapp:+14155238886"

# ✅ YOUR FINAL NUMBERS (ALL MUST JOIN SANDBOX)
TO_WHATSAPP_LIST = [
    "whatsapp:+917760378491",
    "whatsapp:+919606382465",
    "whatsapp:+916360106281",
    "whatsapp:+918105680625"
]

def send_alert(message):

    print("🚀 Sending Alert...")

    # Check credentials
    if not ACCOUNT_SID or not AUTH_TOKEN:
        print("❌ Missing Twilio credentials")
        return

    try:
        # 📍 Get automatic location
        lat, lon, maps_link = get_location()

        # 🔥 Final message
        full_message = f"""
🚨 OVERCROWD ALERT 🚨

{message}

📍 LIVE LOCATION:
Latitude: {lat}
Longitude: {lon}

🗺️ Google Maps:
{maps_link}
"""

        client = Client(ACCOUNT_SID, AUTH_TOKEN)

        for number in TO_WHATSAPP_LIST:
            print(f"➡️ Sending to {number}")

            msg = client.messages.create(
                body=full_message,
                from_=FROM_WHATSAPP,
                to=number
            )

            print(f"✅ Sent to {number} | SID: {msg.sid}")

    except Exception as e:
        print("❌ ERROR:", e)