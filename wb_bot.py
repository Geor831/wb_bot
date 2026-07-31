import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import requests
import io
import re
import sys
import traceback
import PyPDF2
import json

VK_TOKEN = "vk1.a.ImiBmT1KOgvOzJp4nknQ0iZRy9DSmbtIv8FheyPq2K3t4Z8cbpWoHarPFaN8RF_b8X8EC07nuXZ-TVio1YcFeJ_-_LX7MMCtEf5FGmjbn9dQMZk8wkGz3n8bdMj1CGzFoq4ctFCok7PCAIMmdjnVr_yjQgssdVCj8wguoOQP8ibYdIGLIO4WBPL_YVCrTBISMsVv-S6KD1NJDP3lgVM7Zg"
GROUP_ID = 228196102
AITUNNEL_KEY = "sk-aitunnel-mAZ89Pdr1elwujJMKcMQ7ChEsODz0OFk"

def call_deepseek(prompt, system_prompt="Ты — эксперт по маркетплейсам. Отвечай на русском, структурированно, с заголовками и списками."):
    url = "https://api.aitunnel.ru/v1/chat/completions"
    headers = {"Authorization": f"Bearer {AITUNNEL_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ Ошибка AI: {resp.status_code}"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("📊 Аналитика", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🔧 Улучшение", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("🎓 Обучение", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("🏆 Конкуренты", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("✍️ Ответы", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("📈 Юнит", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("💡 Маркетинг", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("📦 Запасы", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("🎯 Нейминг", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("Помощь", color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_back_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("🔙 Меню", color=VkKeyboardColor.PRIMARY)
    return keyboard

def send_msg(user_id, message, keyboard=None):
    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=0,
        keyboard=keyboard.get_keyboard() if keyboard else None
    )

user_data = {}

try:
    print("🔍 Запуск бота с 9 режимами...")
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    vk.groups.getById(group_id=GROUP_ID)
    print("✅ Токен валиден.")
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("✅ Бот готов!")

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            msg = event.obj.message
            if msg:
                user_id = msg['from_id']
                text = msg.get('text', '').strip().lower()
                attachments = msg.get('attachments', [])

                if user_id not in user_data:
                    user_data[user_id] = {"mode": None, "analysis": None, "recs": None, "teach_answers": {}, "step": 0}

                # ---- Быстрые команды ----
                if text.startswith("/"):
                    cmd = text[1:]
                    if cmd == "меню":
                        send_msg(user_id, "📌 *Главное меню*", get_main_keyboard())
                        user_data[user_id]["mode"] = None
                        continue
                    elif cmd == "аналитика":
                        user_data[user_id]["mode"] = "analytics"
                        send_msg(user_id, "📊 Режим *Аналитика*. Пришлите PDF с отзывами.", get_back_keyboard())
                        continue
                    elif cmd == "улучшение":
                        if user_data[user_id]["analysis"] is None:
                            send_msg(user_id, "⚠️ Сначала выполните анализ.")
                            continue
                        user_data[user_id]["mode"] = "improve"
                        prompt = f"На основе анализа отзывов:\n{user_data[user_id]['analysis']}\n\nСоставь 5 рекомендаций по улучшению карточки в виде чек-листа."
                        recs = call_deepseek(prompt)
                        user_data[user_id]["recs"] = recs
                        send_msg(user_id, f"📝 *Рекомендации*\n{recs}", get_back_keyboard())
                        continue
                    elif cmd == "обучение":
                        user_data[user_id]["mode"] = "teach"
                        user_data[user_id]["teach_answers"] = {}
                        user_data[user_id]["step"] = 0
                        send_msg(user_id, "🎓 *Обучение*\n1️⃣ Что за товар?", get_back_keyboard())
                        continue
                    elif cmd == "конкуренты":
                        user_data[user_id]["mode"] = "competitors"
                        send_msg(user_id, "🏆 *Анализ конкурентов*\nОтправьте артикулы через запятую (например: 157065568, 157065569)", get_back_keyboard())
                        continue
                    elif cmd == "ответы":
                        user_data[user_id]["mode"] = "replies"
                        send_msg(user_id, "✍️ *Генератор ответов*\nСкопируйте отзыв (негативный или нейтральный), я напишу 3 варианта ответа.", get_back_keyboard())
                        continue
                    elif cmd == "юнит":
                        user_data[user_id]["mode"] = "unit"
                        send_msg(user_id, "📈 *Юнит-экономика*\nВведите данные через запятую: цена продажи, себестоимость, логистика, комиссия, реклама (пример: 500,200,50,30,20)", get_back_keyboard())
                        continue
                    elif cmd == "маркетинг":
                        user_data[user_id]["mode"] = "marketing"
                        send_msg(user_id, "💡 *Маркетинговые идеи*\nОпишите товар в 2-3 словах (например: кокосовые сливки натуральные), я предложу идеи.", get_back_keyboard())
                        continue
                    elif cmd == "запасы":
                        user_data[user_id]["mode"] = "stock"
                        send_msg(user_id, "📦 *Планирование запасов*\nНапишите артикул товара, я проанализирую сезонность и отзывы для прогноза.", get_back_keyboard())
                        continue
                    elif cmd == "нейминг":
                        user_data[user_id]["mode"] = "naming"
                        send_msg(user_id, "🎯 *Нейминг и позиционирование*\nОпишите товар (категория, преимущества), я предложу названия и слоганы.", get_back_keyboard())
                        continue
                    else:
                        send_msg(user_id, "❌ Неизвестная команда. Напишите /меню.")
                        continue

                # ---- Текстовые команды ----
                if text == "меню":
                    send_msg(user_id, "📌 *Главное меню*", get_main_keyboard())
                    user_data[user_id]["mode"] = None
                    continue

                if text == "конкуренты":
                    user_data[user_id]["mode"] = "competitors"
                    send_msg(user_id, "🏆 *Анализ конкурентов*\nОтправьте артикулы через запятую.", get_back_keyboard())
                    continue
                if text == "ответы":
                    user_data[user_id]["mode"] = "replies"
                    send_msg(user_id, "✍️ *Генератор ответов*\nСкопируйте отзыв.", get_back_keyboard())
                    continue
                if text == "юнит":
                    user_data[user_id]["mode"] = "unit"
                    send_msg(user_id, "📈 *Юнит-экономика*\nВведите: цена, себестоимость, логистика, комиссия, реклама через запятую.", get_back_keyboard())
                    continue
                if text == "маркетинг":
                    user_data[user_id]["mode"] = "marketing"
                    send_msg(user_id, "💡 *Маркетинговые идеи*\nОпишите товар в 2-3 словах.", get_back_keyboard())
                    continue
                if text == "запасы":
                    user_data[user_id]["mode"] = "stock"
                    send_msg(user_id, "📦 *Планирование запасов*\nНапишите артикул товара.", get_back_keyboard())
                    continue
                if text == "нейминг":
                    user_data[user_id]["mode"] = "naming"
                    send_msg(user_id, "🎯 *Нейминг и позиционирование*\nОпишите товар.", get_back_keyboard())
                    continue

                if text in ["помощь", "help"]:
                    send_msg(user_id, "📖 *Справка*\nВсе команды: /меню, /аналитика, /улучшение, /обучение, /конкуренты, /ответы, /юнит, /маркетинг, /запасы, /нейминг")
                    continue

                # ---- Обработка режимов ----
                mode = user_data[user_id]["mode"]

                # 1. Аналитика (PDF)
                if mode == "analytics":
                    pdf_att = None
                    for att in attachments:
                        if att['type'] == 'doc' and att['doc']['ext'] == 'pdf':
                            pdf_att = att['doc']
                            break
                    if pdf_att:
                        send_msg(user_id, "📄 Анализирую PDF через AI...")
                        try:
                            pdf_url = pdf_att['url']
                            resp = requests.get(pdf_url, timeout=30)
                            if resp.status_code == 200:
                                reader = PyPDF2.PdfReader(io.BytesIO(resp.content))
                                full_text = ""
                                for page in reader.pages:
                                    full_text += page.extract_text() or ""
                                if not full_text:
                                    send_msg(user_id, "❌ Не удалось извлечь текст.")
                                    continue
                                prompt = f"Проанализируй отзывы. Выдели рейтинг, плюсы, минусы, топ-10 слов.\n\n{full_text[:8000]}"
                                analysis = call_deepseek(prompt, "Ты — аналитик данных.")
                                user_data[user_id]["analysis"] = analysis
                                send_msg(user_id, f"📊 *Анализ отзывов*\n{analysis}")
                                send_msg(user_id, "💡 Хотите улучшить карточку? Напишите /улучшение")
                            else:
                                send_msg(user_id, "❌ Не удалось скачать PDF.")
                        except Exception as e:
                            send_msg(user_id, f"❌ Ошибка: {str(e)[:100]}")
                        continue
                    else:
                        send_msg(user_id, "ℹ️ Пришлите PDF-файл.")
                        continue

                # 2. Улучшение (уже обработано через /улучшение)

                # 3. Обучение
                if mode == "teach":
                    if text in ["стоп", "выход"]:
                        user_data[user_id]["mode"] = None
                        send_msg(user_id, "❌ Выход. Напишите /меню.", get_main_keyboard())
                        continue
                    step = user_data[user_id]["step"]
                    answers = user_data[user_id]["teach_answers"]
                    if step == 0:
                        answers["товар"] = text
                        send_msg(user_id, "2️⃣ Цена товара?")
                    elif step == 1:
                        answers["цена"] = text
                        send_msg(user_id, "3️⃣ Конкуренты?")
                    elif step == 2:
                        answers["конкуренты"] = text
                        send_msg(user_id, "4️⃣ Уникальность?")
                    elif step == 3:
                        answers["уникальность"] = text
                        prompt = f"Товар: {answers['товар']}, цена: {answers['цена']}, конкуренты: {answers['конкуренты']}, уникальность: {answers['уникальность']}. Составь 6 стратегий продажи дороже."
                        strategies = call_deepseek(prompt)
                        send_msg(user_id, f"🎓 *Стратегии*\n{strategies}", get_back_keyboard())
                        user_data[user_id]["mode"] = None
                        continue
                    user_data[user_id]["step"] = step + 1
                    continue

                # 4. Конкуренты
                if mode == "competitors":
                    articles = [x.strip() for x in text.split(',') if x.strip().isdigit()]
                    if articles:
                        send_msg(user_id, f"🔍 Анализирую {len(articles)} артикулов...")
                        prompt = f"Проанализируй конкурентов по артикулам: {', '.join(articles)}. Сравни цены, рейтинги, отзывы. Выдай слабые места каждого."
                        result = call_deepseek(prompt)
                        send_msg(user_id, f"🏆 *Анализ конкурентов*\n{result}", get_back_keyboard())
                        user_data[user_id]["mode"] = None
                    else:
                        send_msg(user_id, "❌ Укажите артикулы через запятую (цифры).")
                    continue

                # 5. Ответы на отзывы
                if mode == "replies":
                    if len(text) > 10:
                        prompt = f"Напиши 3 варианта ответа на отзыв (вежливый, официальный, дружелюбный). Отзыв: {text}"
                        result = call_deepseek(prompt)
                        send_msg(user_id, f"✍️ *Варианты ответов*\n{result}", get_back_keyboard())
                        user_data[user_id]["mode"] = None
                    else:
                        send_msg(user_id, "❌ Напишите полный текст отзыва.")
                    continue

                # 6. Юнит-экономика
                if mode == "unit":
                    parts = [x.strip() for x in text.split(',')]
                    if len(parts) == 5:
                        try:
                            price, cost, logistics, commission, ad = map(float, parts)
                            margin = price - cost - logistics - commission - ad
                            margin_pct = (margin / price) * 100
                            result = f"📈 *Юнит-экономика*\nЦена: {price} ₽\nСебестоимость: {cost} ₽\nЛогистика: {logistics} ₽\nКомиссия: {commission} ₽\nРеклама: {ad} ₽\n\n**Прибыль:** {margin:.2f} ₽\n**Маржинальность:** {margin_pct:.1f}%"
                            send_msg(user_id, result, get_back_keyboard())
                        except:
                            send_msg(user_id, "❌ Введите числа через запятую.")
                        user_data[user_id]["mode"] = None
                    else:
                        send_msg(user_id, "❌ Введите 5 чисел: цена,себестоимость,логистика,комиссия,реклама")
                    continue

                # 7. Маркетинг
                if mode == "marketing":
                    if len(text) > 3:
                        prompt = f"Для товара '{text}' предложи 5 идей для продвижения на Wildberries: акции, рекламные кампании, кросс-продажи."
                        result = call_deepseek(prompt)
                        send_msg(user_id, f"💡 *Маркетинговые идеи*\n{result}", get_back_keyboard())
                        user_data[user_id]["mode"] = None
                    else:
                        send_msg(user_id, "❌ Опишите товар.")
                    continue

                # 8. Запасы
                if mode == "stock":
                    if text.isdigit():
                        send_msg(user_id, f"📦 Анализирую артикул {text}...")
                        prompt = f"На основе данных Wildberries и общих трендов, спрогнозируй спрос на товар с артикулом {text}. Учти сезонность, отзывы."
                        result = call_deepseek(prompt)
                        send_msg(user_id, f"📦 *Прогноз спроса*\n{result}", get_back_keyboard())
                        user_data[user_id]["mode"] = None
                    else:
                        send_msg(user_id, "❌ Отправьте артикул (цифры).")
                    continue

                # 9. Нейминг
                if mode == "naming":
                    if len(text) > 3:
                        prompt = f"Для товара '{text}' предложи 10 вариантов названия (коротких, запоминающихся), 5 слоганов и 3 УТП."
                        result = call_deepseek(prompt)
                        send_msg(user_id, f"🎯 *Нейминг и слоганы*\n{result}", get_back_keyboard())
                        user_data[user_id]["mode"] = None
                    else:
                        send_msg(user_id, "❌ Опишите товар.")
                    continue

                # ---- Если пользователь не в режиме ----
                if user_data[user_id]["mode"] is None:
                    send_msg(user_id, "ℹ️ Напишите /меню для выбора режима.")
                    continue

                send_msg(user_id, "ℹ️ Неизвестная команда. Напишите /меню.")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    traceback.print_exc()
    sys.exit(1)
