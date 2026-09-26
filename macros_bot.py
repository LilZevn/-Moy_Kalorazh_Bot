import telebot
from telebot import types

# 🔑 ВСТАВЬТЕ СЮДА ВАШ ТОКЕН ОТ @BotFather
import os
API_TOKEN = os.environ.get('TELEGRAM_TOKEN')

# Хранилище данных пользователей
user_data = {}

# --- Константы ---
ACTIVITIES = {
    "1.2": "Минимальный (сидячий образ жизни)",
    "1.375": "Низкий (1-3 раза в неделю)",
    "1.55": "Средний (3-5 раз в неделю)",
    "1.725": "Высокий (6-7 раз в неделю)",
    "1.9": "Очень высокий (2 раза в день)",
}

MODES = {
    "deficit": "Дефицит",
    "maintain": "Поддержание",
    "surplus": "Профицит",
}


# --- Вспомогательные функции ---
def get_main_keyboard():
    """Создаёт главную клавиатуру для сброса/старта"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn = types.KeyboardButton("🔄 Начать заново")
    markup.add(btn)
    return markup


def send_main_menu(chat_id, text="Выберите действие:"):
    """Отправляет главное меню с кнопкой старта"""
    bot.send_message(chat_id, text, reply_markup=get_main_keyboard())


# --- Команда /start ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_data[message.chat.id] = {}
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_male = types.InlineKeyboardButton("👨 Мужской", callback_data="gender_male")
    btn_female = types.InlineKeyboardButton("👩 Женский", callback_data="gender_female")
    markup.add(btn_male, btn_female)
    bot.send_message(message.chat.id, "Привет! Я бот для расчёта КБЖУ.\nВыберите ваш пол:", reply_markup=markup)


# --- Обработка выбора пола ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('gender_'))
def callback_gender(call):
    gender = call.data.split('_')[1]
    user_data[call.message.chat.id]['gender'] = gender
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"Пол: {'Мужской' if gender == 'male' else 'Женский'}")
    msg = bot.send_message(call.message.chat.id, "Введите ваш возраст (полных лет):")
    bot.register_next_step_handler(msg, process_age)


# --- Обработка возраста ---
def process_age(message):
    try:
        age = int(message.text)
        if not (10 <= age <= 120): raise ValueError
        user_data[message.chat.id]['age'] = age
        msg = bot.send_message(message.chat.id, "Введите ваш вес (кг):")
        bot.register_next_step_handler(msg, process_weight)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Пожалуйста, введите корректный возраст (10-120).")
        bot.register_next_step_handler(msg, process_age)


# --- Обработка веса ---
def process_weight(message):
    try:
        weight = float(message.text.replace(',', '.'))
        if not (25 <= weight <= 350): raise ValueError
        user_data[message.chat.id]['weight'] = weight
        msg = bot.send_message(message.chat.id, "Введите ваш рост (см):")
        bot.register_next_step_handler(msg, process_height)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Пожалуйста, введите корректный вес (25-350).")
        bot.register_next_step_handler(msg, process_weight)


# --- Обработка роста и переход к активности ---
def process_height(message):
    try:
        height = float(message.text.replace(',', '.'))
        if not (100 <= height <= 250): raise ValueError
        user_data[message.chat.id]['height'] = height

        markup = types.InlineKeyboardMarkup(row_width=1)
        for key, value in ACTIVITIES.items():
            markup.add(types.InlineKeyboardButton(value, callback_data=f"act_{key}"))

        bot.send_message(message.chat.id, "Выберите уровень активности:", reply_markup=markup)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Пожалуйста, введите корректный рост (100-250).")
        bot.register_next_step_handler(msg, process_height)


# --- Обработка выбора активности и переход к режиму ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('act_'))
def callback_activity(call):
    act_key = call.data.split('_')[1]
    user_data[call.message.chat.id]['activity'] = float(act_key)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"Активность: {ACTIVITIES[act_key]}")

    markup = types.InlineKeyboardMarkup(row_width=3)
    btn_def = types.InlineKeyboardButton("📉 Дефицит", callback_data="mode_deficit")
    btn_maint = types.InlineKeyboardButton("⚖️ Поддержание", callback_data="mode_maintain")
    btn_sur = types.InlineKeyboardButton("📈 Профицит", callback_data="mode_surplus")
    markup.add(btn_def, btn_maint, btn_sur)

    bot.send_message(call.message.chat.id, "Выберите режим калорийности:", reply_markup=markup)


# --- Обработка выбора режима и переход к проценту ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('mode_'))
def callback_mode(call):
    mode = call.data.split('_')[1]
    user_data[call.message.chat.id]['mode'] = mode
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"Режим: {MODES[mode]}")

    if mode == 'maintain':
        user_data[call.message.chat.id]['percent'] = 0
        calculate_and_send(call.message.chat.id)
    else:
        msg = bot.send_message(call.message.chat.id, "Введите процент (например, 15):")
        bot.register_next_step_handler(msg, process_percent)


# --- Обработка процента и расчёт ---
def process_percent(message):
    try:
        percent = float(message.text.replace(',', '.'))
        if not (5 <= percent <= 40): raise ValueError
        user_data[message.chat.id]['percent'] = percent
        calculate_and_send(message.chat.id)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Пожалуйста, введите корректный процент (5-40).")
        bot.register_next_step_handler(msg, process_percent)


# --- Функция расчёта и отправки результата ---
def calculate_and_send(chat_id):
    data = user_data.get(chat_id)
    if not data:
        bot.send_message(chat_id, "Что-то пошло не так. Попробуйте /start")
        return

    # Расчёт BMR
    if data['gender'] == 'male':
        bmr = 10 * data['weight'] + 6.25 * data['height'] - 5 * data['age'] + 5
    else:
        bmr = 10 * data['weight'] + 6.25 * data['height'] - 5 * data['age'] - 161

    tdee = bmr * data['activity']

    mode = data['mode']
    percent = data['percent']

    if mode == 'maintain':
        final_tdee = tdee
        mode_label = "Поддержание веса"
    else:
        if mode == 'deficit':
            final_tdee = tdee * (1 - percent / 100)
            mode_label = f"Дефицит {percent:g}%"
        else:
            final_tdee = tdee * (1 + percent / 100)
            mode_label = f"Профицит {percent:g}%"

    # БЖУ
    protein = data['weight'] * 2.0
    fat = data['weight'] * 1.0
    carbs = (final_tdee - (protein * 4 + fat * 9)) / 4

    warning = ""
    if carbs < 0:
        fat = data['weight'] * 0.6
        carbs = (final_tdee - (protein * 4 + fat * 9)) / 4
        warning = "\n⚠ Калорий мало — жиры снижены до 0.6 г/кг."
        if carbs < 0:
            protein = data['weight'] * 1.6
            carbs = max((final_tdee - (protein * 4 + fat * 9)) / 4, 0)
            warning = "\n⚠ Калорий критически мало — белки снижены до 1.6 г/кг, жиры до 0.6 г/кг."

    # Прогноз
    forecast = ""
    if percent != 0:
        delta = tdee - final_tdee
        kg_week = (delta * 7) / 7700
        if abs(kg_week) > 0.01:
            direction = "сбросите" if kg_week > 0 else "наберёте"
            forecast = f"\n📊 Прогноз: примерно {direction} {abs(kg_week):.2f} кг в неделю ({abs(kg_week * 4.33):.2f} кг в месяц)."

    result_text = (
        f"📊 **Ваш результат:**\n\n"
        f"BMR (базовый обмен): {bmr:,.0f} ккал\n"
        f"TDEE (поддержание): {tdee:,.0f} ккал\n"
        f"Режим: {mode_label}\n"
        f"**Целевая калорийность: {final_tdee:,.0f} ккал**\n\n"
        f"🍗 Белки: {protein:,.0f} г ({protein * 4:,.0f} ккал)\n"
        f"🥑 Жиры: {fat:,.0f} г ({fat * 9:,.0f} ккал)\n"
        f"🍚 Углеводы: {carbs:,.0f} г ({carbs * 4:,.0f} ккал)"
        f"{forecast}"
        f"{warning}"
    )

    bot.send_message(chat_id, result_text, parse_mode='Markdown')
    send_main_menu(chat_id, "Нажмите кнопку, чтобы начать заново:")


# --- Обработка кнопки "Начать заново" ---
@bot.message_handler(func=lambda message: message.text == "🔄 Начать заново")
def restart(message):
    send_welcome(message)


# --- Запуск бота ---
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()