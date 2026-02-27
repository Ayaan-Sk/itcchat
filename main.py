from flask import Flask, request
import requests
import os
from datetime import datetime

app = Flask(__name__)  # ← FIXED: was 'main = Flask(__name__)'

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
WHATSAPP_TOKEN  = "EAApIEQZAK9HoBQ8EUwI0RgYkTl804d9MVjH7XAfHwkyEL1YFm48zABWPpMI15E3CxT9XNkoROeZCQJChy5cDsHykErFZAD4VondnGKfQa1BjrlEnq4FHsF8y18yFLQqkD5G9mLdpfzT8Yhda7qZAfCvNObBY5qIfj5oWp57jyk4zIZBr89SIUXIwUT6V7wTehrBUUHPElJB6vjJyutnWmVenxvroDdPEEtOTrBq2s9Dp36AJgGea6JsnZC6V6iOuyxox1n76ZAQKUL1aK9lVDJcsWZAUYr8ZD"       # ⚠️ Reset your old token in Meta Dashboard!
PHONE_NUMBER_ID = "1020886211104440"
VERIFY_TOKEN    = "itc_verify_123"
AGENT_NUMBER    = "919823387993"               # ← FIXED: removed +, spaces (must be digits only)

# ─────────────────────────────────────────────
#  SESSION STORE
# ─────────────────────────────────────────────
sessions = {}

STATE_NEW           = "new"
STATE_ASK_NAME      = "ask_name"
STATE_ASK_BUSINESS  = "ask_business"
STATE_ASK_GST       = "ask_gst"
STATE_MAIN_MENU     = "main_menu"
STATE_PART_DETAILS  = "part_details"
STATE_AGENT_CONNECT = "agent_connect"


# ─────────────────────────────────────────────
#  WEBHOOK VERIFICATION (GET)
# ─────────────────────────────────────────────
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verified")
        return challenge, 200
    return "Forbidden", 403


# ─────────────────────────────────────────────
#  WEBHOOK RECEIVER (POST)
# ─────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        changes = data["entry"][0]["changes"][0]["value"]
        if "messages" not in changes:
            return "OK", 200
        message  = changes["messages"][0]
        phone    = message["from"]
        msg_type = message.get("type", "")
        if msg_type == "text":
            user_text = message["text"]["body"].strip()
        elif msg_type == "interactive":
            user_text = message["interactive"]["button_reply"]["id"]
        else:
            send_text(phone, "Please send a text message. 🙏")
            return "OK", 200
        print(f"📩 From {phone}: {user_text}")
        handle_message(phone, user_text)
    except Exception as e:
        print(f"❌ Error: {e}")
    return "OK", 200


# ─────────────────────────────────────────────
#  CONVERSATION HANDLER
# ─────────────────────────────────────────────
def handle_message(phone, text):
    if phone not in sessions:
        sessions[phone] = {"state": STATE_NEW, "name": None, "business": None, "gst": None}

    session    = sessions[phone]
    state      = session["state"]
    text_lower = text.lower().strip()

    if text_lower in ["hi", "hello", "start", "restart", "hey"]:
        sessions[phone] = {"state": STATE_NEW, "name": None, "business": None, "gst": None}
        state = STATE_NEW

    if state == STATE_NEW:
        send_text(phone,
            "🙏 *Welcome to Indian Traders Corporation!*\n\n"
            "We are a trusted supplier of industrial parts and components.\n\n"
            "To serve you better, let's get your basic details first.\n\n"
            "👤 Please tell us your *full name*:"
        )
        sessions[phone]["state"] = STATE_ASK_NAME

    elif state == STATE_ASK_NAME:
        sessions[phone]["name"] = text.title()
        send_text(phone,
            f"Nice to meet you, *{text.title()}*! 😊\n\n"
            "🏢 Do you have a *business name*?\n"
            "If yes, please type it. If not, type *skip*."
        )
        sessions[phone]["state"] = STATE_ASK_BUSINESS

    elif state == STATE_ASK_BUSINESS:
        sessions[phone]["business"] = "N/A" if text_lower == "skip" else text.title()
        send_text(phone,
            "📋 Do you have a *GST Number*?\n"
            "If yes, please enter it. If not, type *skip*."
        )
        sessions[phone]["state"] = STATE_ASK_GST

    elif state == STATE_ASK_GST:
        if text_lower == "skip":
            sessions[phone]["gst"] = "N/A"
        else:
            gst = text.upper().strip()
            if len(gst) != 15:
                send_text(phone, "⚠️ GST number should be 15 characters. Please re-enter or type *skip*.")
                return
            sessions[phone]["gst"] = gst

        name     = sessions[phone]["name"]
        business = sessions[phone]["business"]
        gst      = sessions[phone]["gst"]

        send_text(phone,
            f"✅ *Details Saved!*\n\n"
            f"👤 Name: {name}\n"
            f"🏢 Business: {business}\n"
            f"📋 GST: {gst}\n\n"
            "━━━━━━━━━━━━━━━━━\n"
            "How can we help you today?\n\n"
            "Reply with a number:\n"
            "1️⃣  Enquire about a *Part / Product*\n"
            "2️⃣  *Track* my Order\n"
            "3️⃣  *Talk to an Agent*\n"
            "4️⃣  Know our *Working Hours & Location*"
        )
        sessions[phone]["state"] = STATE_MAIN_MENU

    elif state == STATE_MAIN_MENU:
        if text in ["1", "part", "product", "parts", "enquire"]:
            send_text(phone,
                "🔩 *Part / Product Enquiry*\n\n"
                "Please describe the part you're looking for:\n"
                "• Part name or number\n"
                "• Quantity needed\n"
                "• Any specifications (size, material, brand)\n\n"
                "Type your requirement below 👇"
            )
            sessions[phone]["state"] = STATE_PART_DETAILS

        elif text in ["2", "track", "order"]:
            send_text(phone,
                "📦 *Order Tracking*\n\n"
                "Please share your *Order ID* and we'll check the status.\n"
                "(Example: ITC-2024-0045)"
            )

        elif text in ["3", "agent", "talk"]:
            connect_to_agent(phone)

        elif text in ["4", "hours", "location", "timing"]:
            send_text(phone,
                "🕐 *Working Hours:*\n"
                "Monday – Saturday: 9:00 AM – 7:00 PM\n"
                "Sunday: Closed\n\n"
                "📍 *Location:*\n"
                "Indian Traders Corporation\n"
                "Industrial Area, Phase 2\n"
                "Your City – 000000\n\n"
                "📞 *Call us:* +91-XXXXXXXXXX\n"
                "📧 *Email:* info@indiantraders.com\n\n"
                "Reply *1* to enquire about a part\n"
                "Reply *3* to talk to an agent"
            )
        else:
            send_text(phone,
                "⚠️ Please choose a valid option:\n\n"
                "1️⃣  Part / Product Enquiry\n"
                "2️⃣  Track Order\n"
                "3️⃣  Talk to Agent\n"
                "4️⃣  Working Hours & Location"
            )

    elif state == STATE_PART_DETAILS:
        name     = sessions[phone]["name"]
        business = sessions[phone]["business"]
        gst      = sessions[phone]["gst"]

        send_text(phone,
            "✅ *Enquiry Received!*\n\n"
            f"We've noted your requirement:\n_{text}_\n\n"
            "Our team will get back to you shortly. 🙏\n\n"
            "Reply *3* to connect with an agent immediately."
        )
        send_text(AGENT_NUMBER,
            f"🔔 *NEW PART ENQUIRY*\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"👤 Customer: {name}\n"
            f"🏢 Business: {business}\n"
            f"📋 GST: {gst}\n"
            f"📱 Phone: +{phone}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🔩 Requirement:\n{text}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"⏰ {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
        )
        sessions[phone]["state"] = STATE_MAIN_MENU

    else:
        send_text(phone,
            "👋 Type *Hi* to start over.\n\n"
            "1️⃣  Part Enquiry\n"
            "2️⃣  Track Order\n"
            "3️⃣  Talk to Agent\n"
            "4️⃣  Working Hours"
        )
        sessions[phone]["state"] = STATE_MAIN_MENU


# ─────────────────────────────────────────────
#  CONNECT TO AGENT
# ─────────────────────────────────────────────
def connect_to_agent(phone):
    name     = sessions[phone]["name"]
    business = sessions[phone]["business"]
    gst      = sessions[phone]["gst"]

    send_text(phone,
        "👨‍💼 *Connecting you to our agent...*\n\n"
        "Our team member will reach out to you on WhatsApp shortly.\n\n"
        "⏰ Response time: Within 15–30 minutes during business hours.\n\n"
        "Thank you for contacting *Indian Traders Corporation!* 🙏"
    )
    send_text(AGENT_NUMBER,
        f"🔔 *AGENT CONNECT REQUEST*\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"👤 Name: {name}\n"
        f"🏢 Business: {business}\n"
        f"📋 GST: {gst}\n"
        f"📱 Phone: +{phone}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"⏰ {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
        f"👆 Customer wants to speak with an agent. Please follow up!"
    )
    sessions[phone]["state"] = STATE_AGENT_CONNECT


# ─────────────────────────────────────────────
#  SEND MESSAGE
# ─────────────────────────────────────────────
def send_text(to, message):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message, "preview_url": False}
    }
    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent to {to}: {response.status_code}")
    return response.json()


# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 ITC Bot running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)