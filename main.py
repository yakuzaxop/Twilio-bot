import telebot
from telebot import types
from twilio.rest import Client
from keep_alive import keep_alive

bot_token = "7912574251:AAH6fxAEymnKVrlZcUVPUiF2m0k8wkvAuV0"
bot = telebot.TeleBot(bot_token)

user_data = {}  # chat_id -> {sid, auth, client, number_sid, number, main_sid, main_auth}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.add(
        types.KeyboardButton("/set_twilio – Login Twilio"),
        types.KeyboardButton("/buy_number – Buy a number"),
        types.KeyboardButton("/my_number – View your number"),
        types.KeyboardButton("/get_sms – Get incoming messages"),
        types.KeyboardButton("/release_number – Release your number"),
        types.KeyboardButton("/create_subaccount – Create Subaccount"),
        types.KeyboardButton("/list_subaccounts – List Subaccounts"),
        types.KeyboardButton("/use_main_account – Use Main Account"),
        types.KeyboardButton("/reset_twilio – Reset Twilio")
    )
    bot.send_message(message.chat.id, "👋 Welcome to the Twilio Telegram Bot!\nChoose a command from below:", reply_markup=markup)

@bot.message_handler(commands=['set_twilio'])
def set_twilio(message):
    msg = bot.send_message(message.chat.id, "🔑 Send your Twilio `SID | AUTH_TOKEN`:\n(Example: ACxxx | xxxx)")
    bot.register_next_step_handler(msg, save_twilio)

def save_twilio(message):
    try:
        sid, auth = [x.strip() for x in message.text.split("|")]
        client = Client(sid, auth)
        client.api.accounts(sid).fetch()
        user_data[message.chat.id] = {
            "sid": sid,
            "auth": auth,
            "client": client,
            "number": None,
            "number_sid": None,
            "main_sid": sid,
            "main_auth": auth,
        }
        bot.send_message(message.chat.id, "✅ Twilio credentials saved as MAIN account.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")

@bot.message_handler(commands=['reset_twilio'])
def reset_twilio(message):
    if message.chat.id in user_data:
        user_data.pop(message.chat.id)
        bot.send_message(message.chat.id, "🔄 Twilio credentials reset. Use /set_twilio to login again.")
    else:
        bot.send_message(message.chat.id, "ℹ️ No credentials found. Use /set_twilio to login.")

@bot.message_handler(commands=['create_subaccount'])
def create_subaccount(message):
    if message.chat.id not in user_data:
        bot.send_message(message.chat.id, "❌ Please login first using /set_twilio")
        return
    try:
        main_client = Client(user_data[message.chat.id]["main_sid"], user_data[message.chat.id]["main_auth"])
        subaccount = main_client.api.accounts.create(friendly_name=f"Subaccount for {message.chat.id}")
        bot.send_message(message.chat.id, f"✅ Subaccount created!\nSID: {subaccount.sid}\nStatus: {subaccount.status}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Failed to create subaccount: {e}")

@bot.message_handler(commands=['list_subaccounts'])
def list_subaccounts(message):
    if message.chat.id not in user_data:
        bot.send_message(message.chat.id, "❌ Please login first using /set_twilio")
        return
    try:
        main_client = Client(user_data[message.chat.id]["main_sid"], user_data[message.chat.id]["main_auth"])
        subs = main_client.api.accounts.list(limit=20)
        text = "📋 Subaccounts:\n"
        count = 0
        for acc in subs:
            if acc.sid != user_data[message.chat.id]["main_sid"]:
                text += f"- {acc.friendly_name} (SID: {acc.sid}, Status: {acc.status})\n"
                count += 1
        if count == 0:
            text = "ℹ️ No subaccounts found."
        bot.send_message(message.chat.id, text)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Failed to list subaccounts: {e}")

@bot.message_handler(commands=['use_main_account'])
def use_main_account(message):
    if message.chat.id not in user_data:
        bot.send_message(message.chat.id, "❌ Please login first using /set_twilio")
        return
    data = user_data[message.chat.id]
    data["sid"] = data["main_sid"]
    data["auth"] = data["main_auth"]
    data["client"] = Client(data["main_sid"], data["main_auth"])
    bot.send_message(message.chat.id, "✅ Switched to MAIN Twilio account.")

# ---- আগের কোডের ফাংশনগুলো নিচে থাকবে ঠিক আগের মতোই ----

@bot.message_handler(commands=['buy_number'])
def buy_number(message):
    if message.chat.id not in user_data:
        bot.send_message(message.chat.id, "❌ Please login first using /set_twilio")
        return
    msg = bot.send_message(message.chat.id, "📍 Enter Canadian area code (e.g., 437, 587):")
    bot.register_next_step_handler(msg, process_area_code)

def process_area_code(message):
    area_code = message.text.strip()
    client = user_data[message.chat.id]["client"]
    try:
        numbers = client.available_phone_numbers("CA").local.list(area_code=area_code, limit=5)
        if not numbers:
            bot.send_message(message.chat.id, f"No numbers found for {area_code}")
            return
        markup = types.InlineKeyboardMarkup()
        for num in numbers:
            markup.add(types.InlineKeyboardButton(num.phone_number, callback_data=f"buy|{num.phone_number}"))
        bot.send_message(message.chat.id, "Select a number to buy:", reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, "Please login using /set_twilio first.")
        return
    client = user_data[chat_id]["client"]
    if call.data.startswith("buy|"):
        number = call.data.split("|")[1]
        try:
            incoming = client.incoming_phone_numbers.create(phone_number=number)
            user_data[chat_id]["number"] = number
            user_data[chat_id]["number_sid"] = incoming.sid
            bot.send_message(chat_id, f"✅ Number {number} purchased.")
        except Exception as e:
            bot.send_message(chat_id, f"❌ Purchase failed: {e}")

@bot.message_handler(commands=['my_number'])
def my_number(message):
    data = user_data.get(message.chat.id)
    if data and data.get("number"):
        bot.send_message(message.chat.id, f"📱 Your Twilio number: {data['number']}")
    else:
        bot.send_message(message.chat.id, "❌ No number purchased yet.")

@bot.message_handler(commands=['get_sms'])
def get_sms(message):
    data = user_data.get(message.chat.id)
    if not data or not data.get("number"):
        bot.send_message(message.chat.id, "❌ No number found.")
        return
    try:
        messages = data["client"].messages.list(to=data["number"], limit=5)
        if not messages:
            bot.send_message(message.chat.id, "📭 No messages received yet.")
            return
        text = "📜 Last messages:\n\n"
        for msg in messages:
            text += f"From: {msg.from_}\nBody: {msg.body}\n---\n"
        bot.send_message(message.chat.id, text)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")

@bot.message_handler(commands=['release_number'])
def release_number(message):
    data = user_data.get(message.chat.id)
    if not data or not data.get("number_sid"):
        bot.send_message(message.chat.id, "❌ No number to release.")
        return
    try:
        data["client"].incoming_phone_numbers(data["number_sid"]).delete()
        user_data[message.chat.id]["number"] = None
        user_data[message.chat.id]["number_sid"] = None
        bot.send_message(message.chat.id, "🗑 Number released.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")

# Keep alive
keep_alive()

print("🤖 Bot is running...")
bot.polling()