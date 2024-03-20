import os
import requests
import pandas as pd
import telebot
from io import BytesIO
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# إعداد البوت
bot = telebot.TeleBot("7122748860:AAEvuPFW3XjXvNEU6gkUCmn14t-MdHbfXG4")

# متغير عالمي لتخزين العملة المختارة
currency = None

# قاموس لتخزين آخر وقت تم فيه استخدام البوت لكل مستخدم
last_usage_times = {}

def fetch_binance_data(symbol, interval, limit):
    # URL لاسترداد البيانات التاريخية
    url = f"https://api.binance.com/api/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()

    # تحويل البيانات إلى DataFrame
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])

    # تحويل الأعمدة إلى الأنواع المناسبة
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)

    return df

def plot_chart(data):
    x = np.arange(len(data))
    y = data

    plt.plot(x, y)
    plt.title('مثال على مخطط')
    plt.xlabel('المحور السيني')
    plt.ylabel('المحور الصادي')

    # حفظ المخطط كصورة مؤقتة
    image_path = 'chart_temp.png'
    plt.savefig(image_path)

    return image_path

def send_chart_image(chat_id, image_path):
    with open(image_path, 'rb') as chart:
        bot.send_document(chat_id, chart)

def generate_time_frame_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    # إضافة أزرار لاختيار الفريم
    btn_1h = telebot.types.InlineKeyboardButton('1 hour', callback_data='1h')
    btn_4h = telebot.types.InlineKeyboardButton('4 hours', callback_data='4h')
    btn_1d = telebot.types.InlineKeyboardButton('1 day', callback_data='1d')
    markup.add(btn_1h, btn_4h, btn_1d)
    return markup

def record_last_usage(user_id):
    last_usage_times[user_id] = datetime.now()

def check_daily_usage(user_id):
    if user_id not in last_usage_times:
        return True
    last_usage = last_usage_times[user_id]
    today = datetime.now().date()
    return last_usage.date() != today

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Welcome to Binance Data Bot! Please enter the name of the cryptocurrency you want to analyze:")

@bot.message_handler(func=lambda message: True)
def handle_currency(message):
    global currency
    currency = message.text.upper()
    bot.send_message(message.chat.id, f"You chose {currency}. Now select a time frame.", reply_markup=generate_time_frame_markup())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global currency

    def process_time_frame(time_frame, user_id):
        interval = call.data
        bot.send_message(call.message.chat.id, f"You chose {time_frame}. Processing your request...")

        # استخدام التعيينات السابقة للعملة والفريم لجلب البيانات
        df = fetch_binance_data(currency + "USDT", interval, limit=1000)
        image_path = plot_chart(df['close'].values)

        # إرسال الصورة كمستند
        with open(image_path, 'rb') as image:
            bot.send_document(call.message.chat.id, image)

        os.remove(image_path)  # حذف الصورة المؤقتة بعد الإرسال

        # حفظ البيانات في ملف CSV
        file_path = f'{currency.lower()}_data.csv'
        df.to_csv(file_path)

        # إرسال ملف البيانات كمستند
        with open(file_path, 'rb') as file:
            bot.send_document(call.message.chat.id, file)
        
        os.remove(file_path)  # حذف ملف البيانات بعد الإرسال

        record_last_usage(user_id)

    if call.data in ['1h', '4h', '1d']:
        if currency:
            if check_daily_usage(call.from_user.id):
                process_time_frame(call.data, call.from_user.id)
            else:
                bot.send_message(call.message.chat.id, "Sorry, you've already used the bot today.")
        else:
            bot.send_message(call.message.chat.id, "Please choose a currency first.")

# بدء تشغيل البوت
bot.polling()
