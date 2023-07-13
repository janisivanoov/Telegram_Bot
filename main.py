import telebot
import requests
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

API_TOKEN = '5440391805:AAG66fa_qZz6Yu9pfKtB2enJ_312c2FJ3mg'
PLISIO_API_KEY = 'YOUR_PLISIO_API_KEY_HERE'
PRODAMUS_API_KEY = 'YOUR_PRODAMUS_API_KEY_HERE'

conn = sqlite3.connect('files.db')

cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT,
    name TEXT,
    file BLOB
)
''')

data = [
    ('Canada', 'file_1', b'file_data_1')
]

cursor.executemany('INSERT INTO files (country, name, file) VALUES (?, ?, ?)', data)

conn.commit()

conn.close()

bot = telebot.TeleBot(API_TOKEN)

products = {
    'item1': {
        'name': 'Item 1',
        'price': 10.99,
        'country': 'Canada',
        'sold': 0,
        'available': 1200
    },
    'item2': {
        'name': 'Item 2',
        'price': 20.99,
        'country': 'Canada',
        'sold': 0,
        'available': 1200
    },
}

# Add a list of admin user ids
admins = [YOUR_ADMIN_ID_1]

def create_payment(payment_method, item_id):
    item = products[item_id]
    if payment_method == 'plisio':
        url = 'https://plisio.net/api/createinvoice'
        data = {
            'api_key': PLISIO_API_KEY,
            'amount': item['price'],
            'currency': 'USD',
            'item_name': item['name'],
            'item_desc': item['country'],
        }
        response = requests.post(url, data=data).json()
        if response['status'] == 'success':
            products[item_id]['sold'] += 1
            products[item_id]['available'] -= 1
            return f'https://plisio.net/invoice/{response["invoice_id"]}'
    elif payment_method == 'prodamus':
        url = 'https://prodamus.com/api/createinvoice'
        data = {
            'api_key': PRODAMUS_API_KEY,
            'amount': item['price'],
            'currency': 'USD',
            'item_name': item['name'],
            'item_desc': item['country'],
        }
        response = requests.post(url, data=data).json()
        if response['status'] == 'success':
            products[item_id]['sold'] += 1
            products[item_id]['available'] -= 1
            return f'https://prodamus.com/invoice/{response["invoice_id"]}'
    return None

def process_menu_selection(message):
    if message.text == "Accounts":
        available_countries = []
        for item_id, item_data in products.items():
            if item_data['country'] not in available_countries:
                available_countries.append(item_data['country'])
                markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, selective=True)
                for country in available_countries:
                    markup.add(country)
        bot.send_message(chat_id=message.chat.id, text='Countries available:', reply_markup=markup)
        bot.register_next_step_handler(message, choose_country)
    elif message.text == "Rules":
        bot.send_message(chat_id=message.chat.id, text='Here are the rules of the shop: ...')
    elif message.text == "Help":
        bot.send_message(chat_id=message.chat.id, text='How can I help you? ...')
    elif message.text == "SMTH":
        bot.send_message(chat_id=message.chat.id, text='How can I help you? ...')
    else:
        bot.send_message(chat_id=message.chat.id, text='Invalid option, please select again.')
        bot.register_next_step_handler(message, process_menu_selection)

def choose_country(message):
    country = message.text
    if country in [item_data['country'] for item_data in products.values()]:
        list_products_by_country(message, country)
        bot.register_next_step_handler(message, buy_product)
    else:
        bot.send_message(chat_id=message.chat.id, text='Invalid country, please select again.')
        bot.register_next_step_handler(message, choose_country)

def list_products_by_country(message, country):
    response = f'Products available in {country}:\n'
    for item_id, item_data in products.items():
        if item_data['country'] == country:
            response += f'{item_id} - {item_data["name"]} ({item_data["price"]})\n'
            bot.reply_to(message, response)

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/buy'))
def buy_product(message):
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, 'Invalid command format. Use /buy [item_id]. Example: /buy item1')
        return
    item_id = parts[1]
    if item_id not in products:
        bot.reply_to(message, f'Item {item_id} not found. Type /list to see the available products.')
        return
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, selective=True)
    markup.add("Plisio", "Prodamus")
    bot.send_message(chat_id=message.chat.id, text='Select payment method:', reply_markup=markup)
    bot.register_next_step_handler(message, process_payment_method, item_id=item_id)

def process_payment_method(message, item_id):
    payment_method = message.text.lower()
    if payment_method not in ['plisio', 'prodamus']:
        bot.reply_to(message, 'Invalid payment method. Only Plisio and Prodamus are supported.')
        return
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, selective=True)
    markup.add("Confirm", "Cancel")
    bot.send_message(chat_id=message.chat.id, text='Confirm payment?', reply_markup=markup)
    bot.register_next_step_handler(message, process_payment_confirmation, payment_method=payment_method, item_id=item_id)

def payment_successful(payment_link):
    return True

def send_payment_receipt(user_id, payment_link):
    print(f'Sending payment receipt to user {user_id} for payment at link {payment_link}')

def send_file(user_id, file):
    try:
        bot.send_document(chat_id=user_id, document=file)
        return True
    except Exception as e:
        print(f'An error occurred while sending the file: {e}')
        return False

def get_file_from_database(country):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('''SELECT file FROM files WHERE country=?''', (country,))
        result = c.fetchone()

        conn.close()

        return result[0] if result is not None else None
    except Exception as e:
        return None

def process_payment_confirmation(message, payment_method, item_id):
    if message.text.lower() == 'confirm':
        payment_link = create_payment(payment_method, item_id)
        if payment_link is None:
            bot.reply_to(message, 'An error occurred while creating the invoice. Please try again later.')
            return
        bot.reply_to(message, f'Please complete the payment at the following link:\n{payment_link}')
        products[item_id]['sold'] += 1
        if payment_successful(payment_link):
            bot.reply_to(message, "Perfect! Payment receipt sent.")
            send_payment_receipt(message.from_user.id, payment_link)
            file = get_file_from_database(message.from_user.country)
            if file is not None:
                send_file(message.from_user.id, file)
            else:
                bot.reply_to(message, 'An error occurred while getting the file from the database. Please try again later.')
        else:
            bot.reply_to(message, "Payment failed. Please try again later.")
    else:
        bot.reply_to(message, 'Payment canceled.')

@bot.message_handler(commands=['sales'])
def show_sales(message):
    if message.from_user.id not in admins:
        bot.reply_to(message, 'Unauthorized access.')
        return
    response = 'Sales:\n'
    for item_id, amount in products[item_id]['sold'].items():
        response += f'{item_id} - {amount} sold\n'
    bot.reply_to(message, response)

def is_admin(user):
    admins = ['admin_username_1', 'admin_username_2']
    return user.username in admins


def add_file_to_database(bot, update, user_data):
    message = update.message
    user = message.from_user
    if is_admin(user):
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Add country", callback_data='add_country')]])
        bot.send_message(chat_id=message.chat_id, text="Please select an option:", reply_markup=reply_markup)
    else:
        bot.send_message(chat_id=message.chat_id, text="You do not have the necessary permissions to access this feature.")

def add_country(bot, update, user_data):
    query = update.callback_query
    bot.edit_message_text(text="Enter the country name:", chat_id=query.message.chat_id, message_id=query.message.message_id)
    bot.register_next_step_handler(query.message, process_country, user_data=user_data)

def process_country(bot, update, user_data):
    message = update.message
    user_data['country'] = message.text
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Add ID", callback_data='add_id')]])
    bot.send_message(chat_id=message.chat_id, text="Enter the item ID:", reply_markup=reply_markup)
    bot.register_next_step_handler(message, process_id, user_data=user_data)

def process_id(bot, update, user_data):
    message = update.message
    user_data['id'] = message.text
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Add name", callback_data='add_name')]])
    bot.send_message(chat_id=message.chat_id, text="Enter the item name:", reply_markup=reply_markup)
    bot.register_next_step_handler(message, process_name, user_data=user_data)

def process_name(bot, update, user_data):
    message = update.message
    user_data['name'] = message.text
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Add file", callback_data='add_file')]])
    bot.send_message(chat_id=message.chat_id, text="Enter the file:", reply_markup=reply_markup)
    bot.register_next_step_handler(message, process_file, user_data=user_data)

def process_file(bot, update, user_data):
    message = update.message
    country = user_data['country']
    item_id = user_data['id']
    name = user_data['name']
    file = message.document.get_file()
    add_to_database(country, item_id, name, file)
    bot.send_message(chat_id=message.chat_id, text="File added successfully.")

database = {}

def add_to_database(country, item_id, name, file):
    if country not in database:
        database[country] = {}
    if item_id not in database[country]:
        database[country][item_id] = {}
    database[country][item_id]['name'] = name
    database[country][item_id]['file'] = file

bot.polling()