import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import requests
import io
import re
import sys
import traceback
from collections import Counter
import PyPDF2

# ===== ВАШИ ДАННЫЕ (новый токен) =====
VK_TOKEN = "vk1.a.ImiBmT1KOgvOzJp4nknQ0iZRy9DSmbtIv8FheyPq2K3t4Z8cbpWoHarPFaN8RF_b8X8EC07nuXZ-TVio1YcFeJ_-_LX7MMCtEf5FGmjbn9dQMZk8wkGz3n8bdMj1CGzFoq4ctFCok7PCAIMmdjnVr_yjQgssdVCj8wguoOQP8ibYdIGLIO4WBPL_YVCrTBISMsVv-S6KD1NJDP3lgVM7Zg"
GROUP_ID = 228196102
# =======================================

POSITIVE_WORDS = {"вкус","качество","хороший","отлично","рекомендую","супер","нравится","класс","лучший","прекрасный","растворяется","удобно","натуральный","свежий","отличный","полезный","доволен","приятный","ароматный","нежный"}
NEGATIVE_WORDS = {"состав","не соответствует","жалко","разочарован","плохо","ужас","дорого","мало","не понравился","не вкус","кукуруза","обман","скрыли","не хватает","недостаток","проблема"}

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
    rating_match = re.search(r'(\d+[,.]\d+)\s*Выбор покупателей', text)
    avg_rating = rating_match.group(1).replace(',', '.') if rating_match else None
    count_match = re.search(r'(\d+[\s]?\d*)\s*оценок', text)
    total_ratings = count_match.group(1).replace(' ', '') if count_match else None
    words = re.findall(r'\b[а-яёa-z]+\b', text.lower())
    stop_words = {"и","в","на","с","по","к","у","о","от","за","из","без","для","как","что","это","очень","был","но","только","ещё","уже","все","всё","его","её","их","ваш","наш","мой","твой","так","вот","да","нет","или","где","когда","потом","сейчас","если","чтобы","пока","ведь","же","ли","бы","при","до"}
    words = [w for w in words if w not in stop_words and len(w) > 2]
    if not words:
        return None
    word_counts = Counter(words)
    positive_found = {}
    negative_found = {}
    for w, cnt in word_counts.most_common(30):
        if w in POSITIVE_WORDS:
            positive_found[w] = cnt
        elif w in NEGATIVE_WORDS:
            negative_found[w] = cnt
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
        return "❌ Не удалось проанализировать файл."
    lines = []
    lines.append("📊 *Анализ отзывов из PDF*")
    if analysis['avg_rating']:
        lines.append(f"⭐ Средний рейтинг: {analysis['avg_rating']}")
    if analysis['total_ratings']:
        lines.append(f"📝 Количество оценок: {analysis['total_ratings']}")
    lines.append(f"📄 Всего слов: {analysis['total_words']}")
    lines.append("")
    if analysis['positive']:
        lines.append("✅ *Частые плюсы:*")
        for word, count in analysis['positive'].items():
            lines.append(f"   • {word} — {count} раз(а)")
    else:
        lines.append("✅ Явных плюсов нет.")
    if analysis['negative']:
        lines.append("\n⚠️ *Частые минусы:*")
        for word, count in analysis['negative'].items():
            lines.append(f"   • {word} — {count} раз(а)")
    else:
        lines.append("\n⚠️ Явных минусов нет.")
    lines.append("\n📌 *Топ-10 слов:*")
    for word, count in list(analysis['top_words'].items())[:10]:
        lines.append(f"   • {word} — {count}")
    return "\n".join(lines)

try:
    print("🔍 Запуск бота WB.Analytics (PDF-анализ)...")
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    # Проверяем, работает ли токен
    vk.groups.getById(group_id=GROUP_ID)
    print("✅ Токен валиден, сообщество найдено.")
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("✅ Бот готов к работе!")

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            msg = event.obj.message
            if msg:
                user_id = msg['from_id']
                text = msg.get('text', '').strip()
                attachments = msg.get('attachments', [])
                pdf_att = None
                for att in attachments:
                    if att['type'] == 'doc' and att['doc']['ext'] == 'pdf':
                        pdf_att = att['doc']
                        break
                if pdf_att:
                    send_msg(user_id, "📄 Получил PDF. Анализирую...")
                    try:
                        pdf_url = pdf_att['url']
                        resp = requests.get(pdf_url, timeout=30)
                        if resp.status_code == 200:
                            analysis = analyze_reviews_from_pdf(resp.content)
                            report = format_analysis_report(analysis)
                            send_msg(user_id, report)
                        else:
                            send_msg(user_id, "❌ Не удалось скачать PDF.")
                    except Exception as e:
                        send_msg(user_id, f"❌ Ошибка: {str(e)[:100]}")
                    continue
                if text.lower() == "начать":
                    send_msg(user_id, "👋 Привет! Пришлите PDF-файл с отзывами с Wildberries, и я сделаю аналитику.")
                elif text.lower() == "помощь":
                    send_msg(user_id, "📖 Инструкция: пришлите PDF-файл, скачанный со страницы отзывов Wildberries.")
                else:
                    send_msg(user_id, "ℹ️ Пришлите PDF-файл с отзывами или напишите 'помощь'.")
except Exception as e:
    print(f"❌ Критическая ошибка: {e}")
    traceback.print_exc()
    sys.exit(1)
