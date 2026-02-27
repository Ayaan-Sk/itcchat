from flask import Flask, request
import requests
import os
from datetime import datetime

app = Flask(__name__)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
WHATSAPP_TOKEN  = "EAApIEQZAK9HoBQ976dKRKRxH5zzUXVpFsZCCjANv7ZCu3rnxp0TrMb9z7INSImj478INbEwB0PnYbji0GUPZCYpQae2UxxqmszsFQZBZAjRmaVLjzKcIbKPjZAM6AKgCae6bcRiO8VCbjbil9GEZA7hcH2YtDmBh6GAYNZBrZCoO8WkeZBZAh43yO9a7xIwCQvkiZCKSQZAeLP5RZA7MNb5DOxzBHTnIisGHeRopWKPvF4mjXlmseSrSAZCqXn8QNP2vXgqmZArZAAoHgeLPjDjTgqCzgOQ1IvKUlHTQZDZD"
PHONE_NUMBER_ID = "1020886211104440"
VERIFY_TOKEN    = "itc_verify_123"
AGENT_NUMBER    = "919823387993"   # digits only, no + or spaces

# ─────────────────────────────────────────────
#  PRODUCT CATEGORIES & DETAILS
#  Edit these to match ITC's actual products
# ─────────────────────────────────────────────
CATEGORIES = {
    "1": {
        "name": "Bearings & Bushings",
        "details": (
            "🔩 *Bearings & Bushings*\n\n"
            "• Ball Bearings (6200 to 6400 series)\n"
            "• Roller Bearings (Taper, Cylindrical)\n"
            "• Thrust Bearings\n"
            "• Bronze & Nylon Bushings\n\n"
            "📦 Brands: SKF, FAG, NTN, NSK, NBC\n"
            "📐 Sizes: As per customer requirement\n"
            "💰 MOQ: 10 pcs"
        )
    },
    "2": {
        "name": "Fasteners & Bolts",
        "details": (
            "🔩 *Fasteners & Bolts*\n\n"
            "• Hex Bolts & Nuts (M4 to M48)\n"
            "• Stud Bolts & Foundation Bolts\n"
            "• Allen Keys & Socket Head Screws\n"
            "• Washers (Plain, Spring, Lock)\n\n"
            "📦 Material: MS, SS 304/316, Galvanized\n"
            "📐 Grade: 4.6, 8.8, 10.9, 12.9\n"
            "💰 MOQ: 50 pcs"
        )
    },
    "3": {
        "name": "Seals & Gaskets",
        "details": (
            "🛡️ *Seals & Gaskets*\n\n"
            "• Oil Seals (Rotary & Lip Seals)\n"
            "• O-Rings (NBR, Viton, Silicon)\n"
            "• Sheet Gaskets (Cork, Rubber, PTFE)\n"
            "• Ring Joint Gaskets\n\n"
            "📦 Brands: NOK, Freudenberg, Parker\n"
            "📐 Sizes: Custom available\n"
            "💰 MOQ: 20 pcs"
        )
    },
    "4": {
        "name": "Hydraulic & Pneumatic Parts",
        "details": (
            "⚙️ *Hydraulic & Pneumatic Parts*\n\n"
            "• Hydraulic Cylinders & Pistons\n"
            "• Control Valves & Pressure Gauges\n"
            "• Pneumatic Fittings & Tubes\n"
            "• Hoses & Couplings\n\n"
            "📦 Brands: Bosch Rexroth, Parker, Festo\n"
            "📐 Pressure Range: Up to 350 bar\n"
            "💰 MOQ: 5 pcs"
        )
    },
    "5": {
        "name": "Power Transmission Parts",
        "details": (
            "⚡ *Power Transmission Parts*\n\n"
            "• V-Belts & Flat Belts\n"
            "• Pulleys & Sprockets\n"
            "• Chains (Roller, Silent)\n"
            "• Couplings (Jaw, Gear, Flange)\n\n"
            "📦 Brands: Gates, Fenner, Rexnord\n"
            "📐 Sizes: Standard & Custom\n"
            "💰 MOQ: 10 pcs"
        )
    },
    "6": {
        "name": "Other",
        "details": None
    }
}

# ─────────────────────────────────────────────
#  STATES
# ─────────────────────────────────────────────
STATE_NEW            = "new"
STATE_ASK_NAME       = "ask_name"
STATE_ASK_BUSINESS   = "ask_business"
STATE_ASK_GST        = "ask_gst"
STATE_MAIN_MENU      = "main_menu"
STATE_PROD_CATEGORY  = "prod_category"
STATE_PROD_OTHER     = "prod_other"
STATE_QUOT_PRODUCT   = "quot_product"
STATE_QUOT_SPEC      = "quot_spec"
STATE_QUOT_QTY       = "quot_qty"
STATE_INQ_MSG        = "inq_msg"
STATE_NEG_PRODUCT    = "neg_product"
STATE_NEG_PREV_PRICE = "neg_prev_price"
STATE_NEG_OFFER      = "neg_offer"
STATE_NEG_QTY        = "neg_qty"
STATE_DONE           = "done"

# ─────────────────────────────────────────────
#  SESSION STORE
# ─────────────────────────────────────────────
sessions = {}


# ─────────────────────────────────────────────
#  WEBHOOK VERIFICATION
# ─────────────────────────────────────────────
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


# ─────────────────────────────────────────────
#  WEBHOOK RECEIVER
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
#  HELPERS
# ─────────────────────────────────────────────
def new_session():
    return {
        "state": STATE_NEW,
        "name": None, "business": None, "gst": None,
        "quot_product": None, "quot_spec": None, "quot_qty": None,
        "inq_msg": None,
        "neg_product": None, "neg_prev_price": None,
        "neg_offer": None, "neg_qty": None,
        "prod_category": None,
    }

def main_menu_text():
    return (
        "━━━━━━━━━━━━━━━━━\n"
        "📋 *What would you like to do?*\n\n"
        "1️⃣  *Product Details* — Browse our catalogue\n"
        "2️⃣  *Request Quotation* — Get a price quote\n"
        "3️⃣  *General Inquiry* — Ask us anything\n"
        "4️⃣  *Negotiation* — Discuss pricing & offer\n\n"
        "Reply with 1, 2, 3 or 4\n"
        "_(Type *0* anytime to talk to our team)_"
    )

def category_menu_text():
    return (
        "🗂️ *Select a Product Category:*\n\n"
        "1️⃣  Bearings & Bushings\n"
        "2️⃣  Fasteners & Bolts\n"
        "3️⃣  Seals & Gaskets\n"
        "4️⃣  Hydraulic & Pneumatic Parts\n"
        "5️⃣  Power Transmission Parts\n"
        "6️⃣  Other / Type my product\n\n"
        "Reply with a number (1–6)"
    )

def notify_agent(phone, section, data_dict):
    session  = sessions[phone]
    name     = session["name"]
    business = session["business"]
    gst      = session["gst"]
    ts       = datetime.now().strftime('%d %b %Y, %I:%M %p')

    lines = [
        f"🔔 *NEW {section.upper()}*",
        "━━━━━━━━━━━━━━━━━",
        f"👤 Customer : {name}",
        f"🏢 Business : {business}",
        f"📋 GST      : {gst}",
        f"📱 Phone    : +{phone}",
        "━━━━━━━━━━━━━━━━━",
    ]
    for k, v in data_dict.items():
        lines.append(f"• {k}: {v}")
    lines += ["━━━━━━━━━━━━━━━━━", f"⏰ {ts}"]
    send_text(AGENT_NUMBER, "\n".join(lines))


# ─────────────────────────────────────────────
#  MAIN HANDLER
# ─────────────────────────────────────────────
def handle_message(phone, text):
    if phone not in sessions:
        sessions[phone] = new_session()

    session    = sessions[phone]
    state      = session["state"]
    text_lower = text.lower().strip()

    # ── Global restart ──
    if text_lower in ["hi", "hello", "start", "restart", "hey"]:
        sessions[phone] = new_session()
        state = STATE_NEW

    # ── Global: 0 = talk to agent (except during onboarding) ──
    if text == "0" and state not in [STATE_NEW, STATE_ASK_NAME, STATE_ASK_BUSINESS, STATE_ASK_GST]:
        notify_agent(phone, "AGENT CONNECT REQUEST", {"Requested from": state})
        send_text(phone,
            "👨‍💼 *Connecting you to our team...*\n\n"
            "Someone will reach out to you on WhatsApp shortly.\n"
            "⏰ Response time: 15–30 mins during business hours.\n\n"
            "Thank you! 🙏 — *Indian Traders Corporation*\n\n"
            "Type *Hi* to start a new conversation."
        )
        sessions[phone]["state"] = STATE_DONE
        return

    # ── Global: menu shortcut ──
    if text_lower == "menu" and state not in [STATE_NEW, STATE_ASK_NAME, STATE_ASK_BUSINESS, STATE_ASK_GST]:
        sessions[phone]["state"] = STATE_MAIN_MENU
        send_text(phone, main_menu_text())
        return

    # ══════════════════════════════════════════
    #  ONBOARDING
    # ══════════════════════════════════════════
    if state == STATE_NEW:
        send_text(phone,
            "🙏 *Welcome to Indian Traders Corporation!*\n\n"
            "We are a trusted supplier of industrial parts & components.\n\n"
            "To serve you better, let's get your basic details first.\n\n"
            "👤 Please enter your *full name*:"
        )
        sessions[phone]["state"] = STATE_ASK_NAME

    elif state == STATE_ASK_NAME:
        sessions[phone]["name"] = text.title()
        send_text(phone,
            f"Nice to meet you, *{text.title()}*! 😊\n\n"
            "🏢 Please enter your *Business Name*.\n"
            "If none, type *skip*."
        )
        sessions[phone]["state"] = STATE_ASK_BUSINESS

    elif state == STATE_ASK_BUSINESS:
        sessions[phone]["business"] = "N/A" if text_lower == "skip" else text.title()
        send_text(phone,
            "📋 Please enter your *GST Number*.\n"
            "If none, type *skip*."
        )
        sessions[phone]["state"] = STATE_ASK_GST

    elif state == STATE_ASK_GST:
        if text_lower == "skip":
            sessions[phone]["gst"] = "N/A"
        else:
            gst = text.upper().strip()
            if len(gst) != 15:
                send_text(phone, "⚠️ GST should be 15 characters. Re-enter or type *skip*.")
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
            + main_menu_text()
        )
        sessions[phone]["state"] = STATE_MAIN_MENU

    # ══════════════════════════════════════════
    #  MAIN MENU
    # ══════════════════════════════════════════
    elif state == STATE_MAIN_MENU:
        if text == "1":
            send_text(phone, category_menu_text())
            sessions[phone]["state"] = STATE_PROD_CATEGORY

        elif text == "2":
            send_text(phone,
                "📝 *Request a Quotation*\n\n"
                "Please enter the *product name* you need a quote for:"
            )
            sessions[phone]["state"] = STATE_QUOT_PRODUCT

        elif text == "3":
            send_text(phone,
                "💬 *General Inquiry*\n\n"
                "Please type your question or message below 👇\n"
                "_(Be as detailed as possible)_"
            )
            sessions[phone]["state"] = STATE_INQ_MSG

        elif text == "4":
            send_text(phone,
                "🤝 *Negotiation*\n\n"
                "Let's discuss pricing for your requirement.\n\n"
                "Please enter the *product name* you want to negotiate on:"
            )
            sessions[phone]["state"] = STATE_NEG_PRODUCT

        else:
            send_text(phone, "⚠️ Please reply with 1, 2, 3 or 4.\n\n" + main_menu_text())

    # ══════════════════════════════════════════
    #  SECTION 1 — PRODUCT DETAILS
    # ══════════════════════════════════════════
    elif state == STATE_PROD_CATEGORY:
        if text in CATEGORIES:
            cat = CATEGORIES[text]
            sessions[phone]["prod_category"] = cat["name"]

            if text == "6":
                send_text(phone,
                    "🔍 Please type the *product name* you're looking for:"
                )
                sessions[phone]["state"] = STATE_PROD_OTHER
            else:
                send_text(phone, cat["details"])
                send_text(phone,
                    "━━━━━━━━━━━━━━━━━\n"
                    "What would you like to do next?\n\n"
                    "2️⃣  Request a *Quotation* for this product\n"
                    "4️⃣  *Negotiate* pricing\n"
                    "0️⃣  *Talk to our team*\n"
                    "Type *menu* to go back"
                )
                sessions[phone]["state"] = STATE_MAIN_MENU
        else:
            send_text(phone, "⚠️ Please reply with a number between 1–6.\n\n" + category_menu_text())

    elif state == STATE_PROD_OTHER:
        product = text.title()
        sessions[phone]["prod_category"] = product
        notify_agent(phone, "PRODUCT DETAILS INQUIRY", {"Product Searched": product})
        send_text(phone,
            f"✅ Got it! You're looking for *{product}*.\n\n"
            "Our team will check availability and get back to you.\n\n"
            "What would you like to do next?\n\n"
            "2️⃣  Request a *Quotation*\n"
            "4️⃣  *Negotiate* pricing\n"
            "0️⃣  *Talk to our team*\n"
            "Type *menu* to go back"
        )
        sessions[phone]["state"] = STATE_MAIN_MENU

    # ══════════════════════════════════════════
    #  SECTION 2 — QUOTATION
    # ══════════════════════════════════════════
    elif state == STATE_QUOT_PRODUCT:
        sessions[phone]["quot_product"] = text.title()
        send_text(phone,
            f"📐 Please share the *specifications* for *{text.title()}*:\n\n"
            "_(e.g. size, grade, material, brand preference, drawing number)_"
        )
        sessions[phone]["state"] = STATE_QUOT_SPEC

    elif state == STATE_QUOT_SPEC:
        sessions[phone]["quot_spec"] = text
        send_text(phone,
            "📦 How many units do you need?\n"
            "_(e.g. 50 pcs, 100 kg)_"
        )
        sessions[phone]["state"] = STATE_QUOT_QTY

    elif state == STATE_QUOT_QTY:
        sessions[phone]["quot_qty"] = text
        product = sessions[phone]["quot_product"]
        spec    = sessions[phone]["quot_spec"]

        notify_agent(phone, "QUOTATION REQUEST", {
            "Product"       : product,
            "Specifications": spec,
            "Quantity"      : text
        })
        send_text(phone,
            f"✅ *Quotation Request Submitted!*\n\n"
            f"📦 Product  : {product}\n"
            f"📐 Specs    : {spec}\n"
            f"🔢 Quantity : {text}\n\n"
            "Our team will send you a detailed quote within *2–4 business hours*. 🙏\n\n"
            "_(Type *0* to talk to someone now)_"
        )
        sessions[phone]["state"] = STATE_MAIN_MENU
        send_text(phone, main_menu_text())

    # ══════════════════════════════════════════
    #  SECTION 3 — GENERAL INQUIRY
    # ══════════════════════════════════════════
    elif state == STATE_INQ_MSG:
        notify_agent(phone, "GENERAL INQUIRY", {"Message": text})
        send_text(phone,
            "✅ *Inquiry Received!*\n\n"
            f"Your message:\n_{text}_\n\n"
            "Our team will respond within *1 business day*. 🙏\n\n"
            "_(Type *0* to talk to someone now)_"
        )
        sessions[phone]["state"] = STATE_MAIN_MENU
        send_text(phone, main_menu_text())

    # ══════════════════════════════════════════
    #  SECTION 4 — NEGOTIATION
    # ══════════════════════════════════════════
    elif state == STATE_NEG_PRODUCT:
        sessions[phone]["neg_product"] = text.title()
        send_text(phone,
            f"💰 What was the *last quoted price* you received for *{text.title()}*?\n\n"
            "_(Enter amount in ₹ per unit, e.g. 450. Type *skip* if first time)_"
        )
        sessions[phone]["state"] = STATE_NEG_PREV_PRICE

    elif state == STATE_NEG_PREV_PRICE:
        sessions[phone]["neg_prev_price"] = "Not provided" if text_lower == "skip" else text
        send_text(phone,
            "💸 What is your *target price / best offer*?\n"
            "_(Enter amount in ₹ per unit, e.g. 380)_"
        )
        sessions[phone]["state"] = STATE_NEG_OFFER

    elif state == STATE_NEG_OFFER:
        sessions[phone]["neg_offer"] = text
        send_text(phone,
            "📦 What *quantity* are you looking to purchase?\n"
            "_(Higher quantity = better pricing)_"
        )
        sessions[phone]["state"] = STATE_NEG_QTY

    elif state == STATE_NEG_QTY:
        product    = sessions[phone]["neg_product"]
        prev_price = sessions[phone]["neg_prev_price"]
        offer      = sessions[phone]["neg_offer"]

        notify_agent(phone, "NEGOTIATION REQUEST", {
            "Product"         : product,
            "Previous Quote"  : prev_price,
            "Customer's Offer": offer,
            "Quantity"        : text
        })
        send_text(phone,
            f"✅ *Negotiation Request Submitted!*\n\n"
            f"📦 Product        : {product}\n"
            f"💰 Previous Quote : {prev_price}\n"
            f"💸 Your Offer     : {offer}\n"
            f"🔢 Quantity       : {text}\n\n"
            "Our team will review and get back to you with the *best possible price*. 🙏\n\n"
            "_(Type *0* to talk to someone now)_"
        )
        sessions[phone]["state"] = STATE_MAIN_MENU
        send_text(phone, main_menu_text())

    # ══════════════════════════════════════════
    #  DONE STATE
    # ══════════════════════════════════════════
    elif state == STATE_DONE:
        send_text(phone,
            "Our team will contact you soon. 🙏\n\n"
            "Type *Hi* to start a new conversation."
        )

    else:
        sessions[phone]["state"] = STATE_MAIN_MENU
        send_text(phone, "👋 " + main_menu_text())


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