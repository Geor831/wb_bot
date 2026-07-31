import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import requests
import io
import re
import sys
import traceback
from collections import Counter
import PyPDF2

VK_TOKEN = "vk1.a.ImiBmT1KOgvOzJp4nknQ0iZRy9DSmbtIv8FheyPq2K3t4Z8cbpWoHarPFaN8RF_b8X8EC07nuXZ-TVio1YcFeJ_-_LX7MMCtEf5FGmjbn9dQMZk8wkGz3n8bdMj1CGzFoq4ctFCok7PCAIMmdjnVr_yjQgssdVCj8wguoOQP8ibYdIGLIO4WBPL_YVCrTBISMsVv-S6KD1NJDP3lgVM7Zg"
GROUP_ID = 228196102

POSITIVE_WORDS = {"вкус","качество","хороший","отлично","рекомендую","супер","нравится","класс","лучший","прекрасный","растворяется","удобно","натуральный","свежий","отличный","полезный","доволен","приятный","ароматный","нежный","качественный","оперативно","быстро"}
NEGATIVE_WORDS = {"состав","не соответствует","жалко","разочарован","плохо","ужас","дорого","мало","не понравился","не вкус","кукуруза","обман","скрыли","не хватает","недостаток","проблема","не указан","скрыт","непонятно","неудобно","срок","годен","просрочка","нет","отсутствует","не докладывают","не работает","не помогло"}

user_last_analysis = {}
user_last_recommendations = {}

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
    stop_words = {"и","в","на","с","по","к","у","о","от","за","из","без","для","как","что","это","очень","был","но","только","ещё","уже","все","всё","его","её","их","ваш","наш","мой","твой","так","вот","да","нет","или","где","когда","потом","сейчас","если","чтобы","пока","ведь","же","ли","бы","при","до","вот","все","этот","того","эти","чем","будет","можно","свой","свои","свою","свое"}
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

def generate_recommendations(analysis):
    if not analysis:
        return ["❌ Недостаточно данных для рекомендаций."]
    recs = []
    recs.append("📝 *Рекомендации по улучшению карточки товара*")
    recs.append("")
    if analysis['negative']:
        recs.append("🔍 На основе выявленных минусов рекомендуем:")
        for word, count in analysis['negative'].items():
            if word in ["состав", "не соответствует", "скрыли", "не указан", "нет", "отсутствует"]:
                recs.append("1️⃣ Добавьте полный и прозрачный состав в карточку (включая все ингредиенты).")
            elif word in ["вкус", "не вкус", "аромат", "не понравился"]:
                recs.append("2️⃣ Усильте описание вкусовых характеристик, добавьте фото с аппетитной подачей.")
            elif word in ["кукуруза", "крахмал"]:
                recs.append("3️⃣ Объясните в описании роль кукурузного крахмала и почему он используется.")
            elif word in ["дорого", "цена", "высокая"]:
                recs.append("4️⃣ Рассмотрите возможность добавить акцент на уникальные свойства или предложить скидку для новых клиентов.")
            elif word in ["упаковка", "неудобно"]:
                recs.append("5️⃣ Обратите внимание на упаковку: возможно, стоит добавить инструкцию по применению или улучшить дизайн.")
            elif word in ["срок", "годен", "просрочка"]:
                recs.append("6️⃣ Убедитесь, что срок годности указан чётко, и рассмотрите возможность более свежих партий.")
            else:
                recs.append(f"• Обратите внимание на проблему с '{word}' и проработайте её в карточке.")
    else:
        recs.append("✅ Явных минусов не найдено. Однако вот универсальные советы для повышения конверсии:")
        recs.append("1️⃣ Добавьте видеообзор товара с демонстрацией использования.")
        recs.append("2️⃣ Разместите инфографику с ключевыми преимуществами.")
        recs.append("3️⃣ Активируйте работу с отзывами: отвечайте на все вопросы и благодарите покупателей.")
        recs.append("4️⃣ Убедитесь, что заголовок содержит ключевые слова, по которым ищут ваш товар.")
        recs.append("5️⃣ Добавьте блок 'С этим товаром покупают' для кросс-продаж.")
    recs.append("")
    recs.append("💡 *Чтобы получить детали по конкретному пункту, напишите его номер (1, 2, 3...)*")
    recs.append("Или напишите 'все' — я повторю все рекомендации.")
    return recs

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
    lines.append("\n---\n💬 *Хотите получить рекомендации по улучшению карточки?* Напишите **«улучшить»**.")
    return "\n".join(lines)

try:
    print("🔍 Запуск бота...")
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    vk.groups.getById(group_id=GROUP_ID)
    print("✅ Токен валиден, сообщество найдено.")
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("✅ Бот готов к работе!")

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            msg = event.obj.message
            if msg:
                user_id = msg['from_id']
                text = msg.get('text', '').strip().lower()
                attachments = msg.get('attachments', [])

                # Если есть сохранённые рекомендации и пользователь пишет цифру
                if user_id in user_last_recommendations and text.isdigit():
                    num = int(text)
                    recs = user_last_recommendations[user_id]
                    found = None
                    for line in recs:
                        if line.startswith(f"{num}️⃣") or line.startswith(f"{num}."):
                            found = line
                            break
                    if found:
                        send_msg(user_id, f"🔹 *Подробнее по пункту {num}:*\n{found}\n\nХотите ещё что-то уточнить? Напишите номер другого пункта или 'все'.")
                    else:
                        send_msg(user_id, f"❌ Пункт с номером {num} не найден.")
                    continue

                # Команда "все" — если есть рекомендации, выводим их, иначе генерируем на основе анализа
                if text == "все":
                    if user_id in user_last_recommendations:
                        send_msg(user_id, "\n".join(user_last_recommendations[user_id]))
                    elif user_id in user_last_analysis:
                        analysis = user_last_analysis[user_id]
                        recs = generate_recommendations(analysis)
                        user_last_recommendations[user_id] = recs
                        send_msg(user_id, "\n".join(recs))
                    else:
                        send_msg(user_id, "ℹ️ Сначала пришлите PDF-файл с отзывами для анализа.")
                    continue

                # Команда "улучшить"
                if text == "улучшить" and user_id in user_last_analysis:
                    analysis = user_last_analysis[user_id]
                    recs = generate_recommendations(analysis)
                    user_last_recommendations[user_id] = recs
                    send_msg(user_id, "\n".join(recs))
                    continue

                # Проверка на PDF
                pdf_att = None
                for att in attachments:
                    if att['type'] == 'doc' and att['doc']['ext'] == 'pdf':
                        pdf_att = att['doc']
                        break
                if pdf_att:
                    send_msg(user_id, "📄 Получил PDF. Анализирую... ⏳")
                    try:
                        pdf_url = pdf_att['url']
                        resp = requests.get(pdf_url, timeout=30)
                        if resp.status_code == 200:
                            analysis = analyze_reviews_from_pdf(resp.content)
                            if analysis:
                                user_last_analysis[user_id] = analysis
                                # Очищаем старые рекомендации
                                if user_id in user_last_recommendations:
                                    del user_last_recommendations[user_id]
                                report = format_analysis_report(analysis)
                                send_msg(user_id, report)
                            else:
                                send_msg(user_id, "❌ Не удалось проанализировать PDF.")
                        else:
                            send_msg(user_id, "❌ Не удалось скачать PDF.")
                    except Exception as e:
                        send_msg(user_id, f"❌ Ошибка: {str(e)[:100]}")
                    continue

                # Обработка команд
                if text in ["начать", "привет"]:
                    send_msg(user_id, "👋 Привет! Я бот для анализа отзывов с Wildberries.\n\n📌 Просто пришлите мне PDF-файл с выгрузкой отзывов.\nЯ выделю главные плюсы, минусы и дам рекомендации по улучшению карточки.\n\nКоманды:\n• помощь — список команд\n• начать — это сообщение")
                elif text == "помощь":
                    send_msg(user_id, "📖 *Справка*\n\n1. Пришлите мне PDF-файл, скачанный со страницы отзывов Wildberries.\n2. Я проанализирую и выдам отчёт.\n3. Затем напишите 'улучшить' — я дам конкретные советы по улучшению карточки.\n4. Чтобы узнать детали по конкретному пункту, напишите его номер (например, 1).\n5. 'все' — повтор всех рекомендаций (или генерация, если ещё не делали).\n\nПример: просто прикрепите файл и отправьте в чат.")
                else:
                    send_msg(user_id, "ℹ️ Чтобы я мог помочь, пришлите PDF-файл с отзывами.\nЕсли нужна инструкция — напишите 'помощь'.")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    traceback.print_exc()
    sys.exit(1)
