import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# 1. Setup your credentials (must be in your .env)
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = "+18382215083"  # Your Twilio Number
my_number = "+919873924855"      # Your Personal Number

client = Client(account_sid, auth_token)

# 2. Your Pinggy/Tunnel URL
# IMPORTANT: This must match the route in your main.py that returns the <Connect><Stream> TwiML
BASE_URL = "http://itsca-103-87-51-95.a.free.pinggy.link"

def make_call():
    print(f"📞 Initializing call to {my_number}...")
    try:
        call = client.calls.create(
            # Twilio will fetch instructions from this URL the moment you pick up
            url=f"{BASE_URL}/voice",
            to=my_number,
            from_=twilio_number
        )
        print(f"✅ Call SID: {call.sid}")
        print("🔔 Check your phone now!")
    except Exception as e:
        print(f"❌ Failed to trigger call: {e}")

if __name__ == "__main__":
    make_call()