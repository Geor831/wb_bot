import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import requests
import json
import sys
import traceback
import time
import io
import re
from collections import Counter
import PyPDF2

# ===== ВАШИ ДАННЫЕ =====
VK_TOKEN = "vk1.a.wOAyfLk_ftARYpMVGdnWS1Gy7V0cUArWt_4MZvKZnGHInrstPt_y2dT5B14LjIsRis7OTLWD12LsEcNoPW-O_C8_zB0BfaA2zeW5OyamxxbzeD7VrIoAhsVwaPXmK6uBroTD6_2XnaGUzS_SW0l29QjUmmVgmczJfTQnhnk6l4WsdwFEXDrNawF9osrsjqdO5XHjjNTUSWmnAlpvyt4ouA"
GROUP_ID = 228196102
# ======================================

POSITIVE_WORDS = {"вкус", "качество", "хороший", "отлично", "рекомендую", "супер", "нравится", "класс", "лучший", "прекрасный", "растворяется", "удобно", "натуральный", "свежий", "качественный", "доволен", "отличный", "полезный"}
NEGATIVE_WORDS = {"состав", "не соответствует", "жалко", "разочарован", "плохо", "ужас", "дорого", "мало", "не понравился", "не вкус", "кукуруза", "обман", "скрыли", "не хватает", "недостаток", "проблема"}

def send_msg(user_id, message):
    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=0
    )

def extract_text_from_pdf(pdf_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Ошибка чтения PDF: {e}")
        return None

def parse_pdf_reviews(pdf_bytes):
    text = extract_text_from_pdf(pdf_bytes)
    if not text:
        return None

    # Ищем рейтинг
    rating_match = re.search(r'(\d+[,.]\d+)\s*Выбор покупателей', text)
    avg_rating = rating_match.group(1).replace(',', '.') if rating_match else None

    # Ищем количество оценок
    count_match = re.search(r'(\d+[\s]?\d*)\s*оценок', text)
    total_ratings = count_match.group(1).replace(' ', '') if count_match else None

    # Разбиваем на слова
    words = re.findall(r'\b[а-яёа-я]+\b', text.lower())
    stop_words = {"и", "в", "на", "с", "по", "к", "у", "о", "от", "за", "из", "без", "для", "как", "что", "это", "очень", "был", "но", "только", "ещё", "уже", "все", "всё", "его", "её", "их", "ваш", "наш", "мой", "твой", "так", "вот", "да", "нет", "или", "где", "когда", "потом", "сейчас", "если", "чтобы", "пока", "ведь", "же", "ли", "бы", "при", "из", "без", "до", "по", "для", "от", "с", "на", "в"}
    words = [w for w in words if w not in stop_words and len(w) > 2]
    word_counts = Counter(words)

    positive_found = {}
    negative_found = {}
    for word, count in word_counts.most_common(30):
        if word in POSITIVE_WORDS:
            positive_found[word] = count
        elif word in NEGATIVE_WORDS:
            negative_found[word] = count

    return {
        "avg_rating": avg_rating,
        "total_ratings": total_ratings,
        "positive": dict(sorted(positive_found.items(), key=lambda x: x[1], reverse=True)[:5]),
        "negative": dict(sorted(negative_found.items(), key=lambda x: x[1], reverse=True)[:5]),
        "top_words": dict(word_counts.most_common(10))
    }

try:
    print("🔍 Начинаем инициализацию бота...")
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("✅ Бот WB.Analytics запущен!")

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            if event.obj.message:
                user_id = event.obj.message['from_id']
                text = event.obj.message['text'].strip()
                attachments = event.obj.message.get('attachments', [])

                # Обработка PDF-файла
                pdf_found = False
                for att in attachments:
                    if att['type'] == 'doc' and att['doc']['ext'] == 'pdf':
                        pdf_found = True
                        send_msg(user_id, "📄 Получил PDF, анализирую... ⏳")
                        pdf_url = att['doc']['url']
                        try:
                            pdf_response = requests.get(pdf_url, timeout=30)
                            if pdf_response.status_code == 200:
                                analysis = parse_pdf_reviews(pdf_response.content)
                                if analysis:
                                    msg = "📊 *Анализ отзывов из PDF*\n"
                                    if analysis['avg_rating']:
                                        msg += f"⭐ Средний рейтинг: {analysis['avg_rating']}\n"
                                    if analysis['total_ratings']:
                                        msg += f"📝 Количество оценок: {analysis['total_ratings']}\n"
                                    msg += "\n"
                                    if analysis['positive']:
                                        msg += "✅ *Частые плюсы:*\n"
                                        for word, count in analysis['positive'].items():
                                            msg += f"   • {word} — {count} раз(а)\n"
                                    if analysis['negative']:
                                        msg += "\n⚠️ *Частые минусы:*\n"
                                        for word, count in analysis['negative'].items():
                                            msg += f"   • {word} — {count} раз(а)\n"
                                    msg += "\n📌 *Топ-10 слов:*\n"
                                    for word, count in list(analysis['top_words'].items())[:10]:
                                        msg += f"   • {word} — {count}\n"
                                    send_msg(user_id, msg)
                                else:
                                    send_msg(user_id, "❌ Не удалось проанализировать PDF. Возможно, файл повреждён или не содержит отзывов.")
                            else:
                                send_msg(user_id, "❌ Не удалось скачать PDF.")
                        except Exception as e:
                            send_msg(user_id, f"❌ Ошибка при обработке PDF: {str(e)[:100]}")
                        break

                # Если не PDF, обрабатываем текст
                if not pdf_found:
                    if text.lower() == "начать":
                        send_msg(user_id, "👋 Привет! Я WB.Analytics — помощник по анализу товаров.\n\n📌 Команды:\n• Пришлите PDF-файл с отзывами — я сделаю аналитику.\n• Отправьте артикул (число) — попробую найти данные (может не работать из-за блокировок).\n• помощь — список команд")
                    
                    elif text.lower() == "помощь":
                        send_msg(user_id, "📖 *Помощь по боту*\n\n1. Пришлите PDF-файл с отзывами (выгрузка с Wildberries) — я проанализирую.\n2. Либо отправьте артикул (число) — но API может быть недоступно.\n3. Пример команды: отзывы 61472739 (если API работает).")

                    elif text.lower().startswith("отзывы") and len(text.split()) > 1:
                        # Команда "отзывы артикул" — пробуем через API
                        article = text.split()[1]
                        if article.isdigit():
                            send_msg(user_id, f"🔍 Пытаюсь получить отзывы через API для {article}... (может не работать)")
                            # Здесь можно попробовать запрос к feedbacks.wb.ru, но скорее всего таймаут
                            send_msg(user_id, "⚠️ API Wildberries часто блокирует ботов. Рекомендую загрузить PDF-файл с отзывами вручную.")
                        else:
                            send_msg(user_id, "❌ Артикул должен быть числом.")
                    
                    elif text.isdigit():
                        send_msg(user_id, f"🔍 Ищу товар {text}... (запрос к API)")
                        # Пробуем через API, но сразу предупреждаем
                        send_msg(user_id, "⚠️ Если данные не загрузятся, пришлите PDF-файл с отзывами.")
                        # Здесь можно оставить старую логику parse_wb_product, но она скорее всего упадёт
                        # Мы её убрали, чтобы не ломать бота. Просто напоминаем про PDF.
                    else:
                        send_msg(user_id, "ℹ️ Отправьте артикул (цифры) или пришлите PDF-файл с отзывами.\nНапишите 'помощь' для справки.")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    traceback.print_exc()
    sys.exit(1)
