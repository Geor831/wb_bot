import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import requests
import io
import re
import sys
import traceback
from collections import Counter
import PyPDF2

# ===== ВАШИ ДАННЫЕ =====
VK_TOKEN = "vk1.a.wOAyfLk_ftARYpMVGdnWS1Gy7V0cUArWt_4MZvKZnGHInrstPt_y2dT5B14LjIsRis7OTLWD12LsEcNoPW-O_C8_zB0BfaA2zeW5OyamxxbzeD7VrIoAhsVwaPXmK6uBroTD6_2XnaGUzS_SW0l29QjUmmVgmczJfTQnhnk6l4WsdwFEXDrNawF9osrsjqdO5XHjjNTUSWmnAlpvyt4ouA"
GROUP_ID = 228196102
# =================================

# Словари позитивных и негативных слов (можно дополнять)
POSITIVE_WORDS = {
    "вкус", "качество", "хороший", "отлично", "рекомендую", "супер",
    "нравится", "класс", "лучший", "прекрасный", "растворяется",
    "удобно", "натуральный", "свежий", "отличный", "полезный",
    "доволен", "приятный", "ароматный", "нежный"
}

NEGATIVE_WORDS = {
    "состав", "не соответствует", "жалко", "разочарован", "плохо",
    "ужас", "дорого", "мало", "не понравился", "не вкус", "кукуруза",
    "обман", "скрыли", "не хватает", "недостаток", "проблема"
}

def send_msg(user_id, message):
    vk.messages.send(user_id=user_id, message=message, random_id=0)

def extract_text_from_pdf(pdf_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        return full_text
    except Exception as e:
        print(f"Ошибка извлечения текста из PDF: {e}")
        return None

def analyze_reviews_from_pdf(pdf_bytes):
    text = extract_text_from_pdf(pdf_bytes)
    if not text:
        return None

    # 1. Извлекаем рейтинг
    rating_match = re.search(r'(\d+[,.]\d+)\s*Выбор покупателей', text)
    avg_rating = rating_match.group(1).replace(',', '.') if rating_match else None

    # 2. Количество оценок
    count_match = re.search(r'(\d+[\s]?\d*)\s*оценок', text)
    total_ratings = count_match.group(1).replace(' ', '') if count_match else None

    # 3. Разбиваем на слова (только русские и английские буквы)
    words = re.findall(r'\b[а-яёa-z]+\b', text.lower())
    stop_words = {"и", "в", "на", "с", "по", "к", "у", "о", "от", "за",
                  "из", "без", "для", "как", "что", "это", "очень", "был",
                  "но", "только", "ещё", "уже", "все", "всё", "его", "её",
                  "их", "ваш", "наш", "мой", "твой", "так", "вот", "да",
                  "нет", "или", "где", "когда", "потом", "сейчас", "если",
                  "чтобы", "пока", "ведь", "же", "ли", "бы", "при", "до"}
    words = [w for w in words if w not in stop_words and len(w) > 2]

    if not words:
        return None

    word_counts = Counter(words)

    # 4. Выделяем частые позитивные и негативные слова
    positive_found = {}
    negative_found = {}
    for w, cnt in word_counts.most_common(30):
        if w in POSITIVE_WORDS:
            positive_found[w] = cnt
        elif w in NEGATIVE_WORDS:
            negative_found[w] = cnt

    # 5. Формируем результат
    return {
        "avg_rating": avg_rating,
        "total_ratings": total_ratings,
        "positive": dict(sorted(positive_found.items(), key=lambda x: x[1], reverse=True)[:5]),
        "negative": dict(sorted(negative_found.items(), key=lambda x: x[1], reverse=True)[:5]),
        "top_words": dict(word_counts.most_common(10)),
        "total_words": len(words)
    }

def format_analysis_report(analysis):
    if not analysis:
        return "❌ Не удалось проанализировать файл. Проверьте, что это PDF с отзывами Wildberries."

    lines = []
    lines.append("📊 *Анализ отзывов из PDF*")
    
    if analysis['avg_rating']:
        lines.append(f"⭐ Средний рейтинг: {analysis['avg_rating']}")
    if analysis['total_ratings']:
        lines.append(f"📝 Количество оценок: {analysis['total_ratings']}")
    lines.append(f"📄 Всего слов в отзывах: {analysis['total_words']}")
    lines.append("")

    if analysis['positive']:
        lines.append("✅ *Часто встречающиеся плюсы:*")
        for word, count in analysis['positive'].items():
            lines.append(f"   • {word} — {count} раз(а)")
    else:
        lines.append("✅ Явных плюсов не обнаружено.")

    if analysis['negative']:
        lines.append("\n⚠️ *Часто встречающиеся минусы:*")
        for word, count in analysis['negative'].items():
            lines.append(f"   • {word} — {count} раз(а)")
    else:
        lines.append("\n⚠️ Явных минусов не обнаружено.")

    lines.append("\n📌 *Топ-10 ключевых слов:*")
    for word, count in list(analysis['top_words'].items())[:10]:
        lines.append(f"   • {word} — {count}")

    return "\n".join(lines)

# ======================== ОСНОВНОЙ ЦИКЛ =========================
try:
    print("🔍 Запуск бота WB.Analytics (PDF-анализ)...")
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("✅ Бот готов к работе!")

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            msg = event.obj.message
            if msg:
                user_id = msg['from_id']
                text = msg.get('text', '').strip()
                attachments = msg.get('attachments', [])

                # -------- Проверяем, есть ли PDF --------
                pdf_att = None
                for att in attachments:
                    if att['type'] == 'doc' and att['doc']['ext'] == 'pdf':
                        pdf_att = att['doc']
                        break

                if pdf_att:
                    send_msg(user_id, "📄 Получил PDF-файл. Идёт анализ... ⏳ (до 20 секунд)")
                    try:
                        pdf_url = pdf_att['url']
                        resp = requests.get(pdf_url, timeout=30)
                        if resp.status_code == 200:
                            analysis = analyze_reviews_from_pdf(resp.content)
                            report = format_analysis_report(analysis)
                            send_msg(user_id, report)
                        else:
                            send_msg(user_id, "❌ Не удалось скачать PDF. Попробуйте ещё раз.")
                    except Exception as e:
                        send_msg(user_id, f"❌ Ошибка при обработке PDF: {str(e)[:100]}")
                    continue  # После PDF ничего не обрабатываем

                # -------- Обработка текстовых команд --------
                if text.lower() == "начать":
                    send_msg(user_id, 
                             "👋 Привет! Я бот для анализа отзывов с Wildberries.\n"
                             "📌 Просто пришлите мне PDF-файл с выгрузкой отзывов.\n"
                             "Я выделю главные плюсы, минусы и ключевые слова.\n\n"
                             "Команды:\n"
                             "• помощь — список команд\n"
                             "• начать — это сообщение")
                elif text.lower() == "помощь":
                    send_msg(user_id,
                             "📖 *Справка*\n\n"
                             "1. Пришлите мне PDF-файл, скачанный со страницы отзывов Wildberries.\n"
                             "2. Я проанализирую текст и выдам:\n"
                             "   - средний рейтинг,\n"
                             "   - частые положительные и отрицательные слова,\n"
                             "   - топ ключевых слов.\n\n"
                             "Пример: просто прикрепите файл и отправьте в чат.")
                else:
                    send_msg(user_id,
                             "ℹ️ Чтобы я мог помочь, пришлите PDF-файл с отзывами.\n"
                             "Если нужна инструкция — напишите 'помощь'.")

except Exception as e:
    print("❌ Критическая ошибка:", e)
    traceback.print_exc()
    sys.exit(1)
