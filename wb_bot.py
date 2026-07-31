import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import requests
import json
import sys
import traceback
import time
from collections import Counter
import re

# ===== ВАШИ ДАННЫЕ =====
VK_TOKEN = "vk1.a.wOAyfLk_ftARYpMVGdnWS1Gy7V0cUArWt_4MZvKZnGHInrstPt_y2dT5B14LjIsRis7OTLWD12LsEcNoPW-O_C8_zB0BfaA2zeW5OyamxxbzeD7VrIoAhsVwaPXmK6uBroTD6_2XnaGUzS_SW0l29QjUmmVgmczJfTQnhnk6l4WsdwFEXDrNawF9osrsjqdO5XHjjNTUSWmnAlpvyt4ouA"
GROUP_ID = 228196102
# ======================================

# Простой словарь позитивных и негативных слов (для бесплатного анализа)
POSITIVE_WORDS = {"вкус", "качество", "хороший", "отлично", "рекомендую", "супер", "нравится", "класс", "лучший", "прекрасный", "растворяется", "удобно", "натуральный", "свежий"}
NEGATIVE_WORDS = {"состав", "не соответствует", "жалко", "разочарован", "плохо", "ужас", "дорого", "мало", "не понравился", "не вкус", "кукуруза", "обман", "скрыли", "не хватает"}

def fetch_with_retry(url, timeout=30, retries=3):
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, timeout=timeout, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            if response.status_code == 200:
                return response
            else:
                print(f"Ошибка HTTP {response.status_code}, попытка {attempt+1}")
        except Exception as e:
            print(f"Ошибка: {e}, попытка {attempt+1}")
            if attempt < retries:
                time.sleep(3)
            else:
                raise
    return None

def parse_reviews(article):
    """Парсит отзывы с Wildberries через публичный эндпоинт"""
    try:
        url = f"https://feedbacks.wb.ru/api/v1/feedbacks?nmId={article}"
        response = fetch_with_retry(url)
        if not response:
            return None
        data = response.json()
        if not data.get('feedbacks'):
            return None
        
        reviews = []
        ratings = []
        for item in data['feedbacks']:
            text = item.get('text', '')
            valuation = item.get('productValuation', 0)
            if text:
                reviews.append(text.lower())
                ratings.append(valuation)
        
        if not reviews:
            return None
        
        # Средний рейтинг
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Анализ частотности слов (простой, без AI)
        all_text = " ".join(reviews)
        words = re.findall(r'\b[а-яёa-z]+\b', all_text)
        word_counts = Counter(words)
        
        # Убираем стоп-слова (служебные)
        stop_words = {"и", "в", "на", "с", "по", "к", "у", "о", "от", "за", "из", "без", "для", "как", "что", "это", "очень", "был", "но", "только", "ещё", "уже", "все", "всё", "его", "её", "их", "ваш", "наш", "мой", "твой", "так", "вот", "да", "нет", "или", "где", "когда", "потом", "сейчас", "если", "чтобы", "пока", "ведь", "же", "ли", "бы"}
        for word in stop_words:
            if word in word_counts:
                del word_counts[word]
        
        # Выделяем позитивные и негативные слова
        positive_found = {}
        negative_found = {}
        for word, count in word_counts.most_common(30):
            if word in POSITIVE_WORDS:
                positive_found[word] = count
            elif word in NEGATIVE_WORDS:
                negative_found[word] = count
        
        return {
            "total": len(reviews),
            "avg_rating": round(avg_rating, 1),
            "positive": dict(sorted(positive_found.items(), key=lambda x: x[1], reverse=True)[:5]),
            "negative": dict(sorted(negative_found.items(), key=lambda x: x[1], reverse=True)[:5]),
            "top_words": dict(word_counts.most_common(10))
        }
    except Exception as e:
        print(f"Ошибка парсинга отзывов: {e}")
        return None

def parse_wb_product(article):
    try:
        detail_url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={article}"
        detail_response = fetch_with_retry(detail_url)
        if not detail_response:
            return None
        detail_data = detail_response.json()
        if not detail_data.get('data', {}).get('products'):
            return None
        product = detail_data['data']['products'][0]
        search_query = product.get('name', '').split('/')[0].strip()
        search_url = f"https://search.wb.ru/exactmatch/ru/common/v18/search?appType=1&curr=rub&lang=ru&page=1&query={search_query}&resultset=catalog&sort=popular&spp=30"
        search_response = fetch_with_retry(search_url)
        if not search_response:
            return None
        search_data = search_response.json()
        competitors = []
        for item in search_data.get('data', {}).get('products', [])[:10]:
            if item.get('id') != int(article):
                competitors.append({
                    "id": item.get('id'),
                    "name": item.get('name'),
                    "price": item.get('sizes', [{}])[0].get('price', {}).get('product', 0) / 100,
                    "rating": item.get('rating', 0),
                    "feedbacks": item.get('feedbacks', 0),
                })
        return {
            "product": {
                "id": product.get('id'),
                "name": product.get('name'),
                "price": product.get('sizes', [{}])[0].get('price', {}).get('product', 0) / 100,
                "rating": product.get('rating', 0),
                "feedbacks": product.get('feedbacks', 0),
            },
            "competitors": competitors[:5]
        }
    except Exception as e:
        print(f"Ошибка парсинга товара: {e}")
        return None

def analyze_product(product, competitors):
    if not competitors:
        return None
    avg_price = sum(c['price'] for c in competitors) / len(competitors)
    avg_rating = sum(c['rating'] for c in competitors) / len(competitors)
    avg_feedbacks = sum(c['feedbacks'] for c in competitors) / len(competitors)
    price_diff = round((product['price'] - avg_price) / avg_price * 100, 1)
    rating_diff = round((product['rating'] - avg_rating) / avg_rating * 100, 1)
    feedbacks_diff = round((product['feedbacks'] - avg_feedbacks) / avg_feedbacks * 100, 1)
    return {
        'price_diff': price_diff,
        'rating_diff': rating_diff,
        'feedbacks_diff': feedbacks_diff,
        'avg_price': round(avg_price, 2),
        'avg_rating': round(avg_rating, 2),
        'avg_feedbacks': round(avg_feedbacks, 0)
    }

def send_msg(user_id, message):
    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=0
    )

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
                
                if text.lower() == "начать":
                    send_msg(user_id, "👋 Привет! Я WB.Analytics — аналитик конкурентов.\n\n📌 Команды:\n• артикул — анализ товара (цена, конкуренты)\n• отзывы артикул — анализ отзывов\n• помощь — список команд")
                
                elif text.lower() == "помощь":
                    send_msg(user_id, "📖 *Помощь по боту*\n\n1. Отправьте артикул (число) — анализ конкурентов.\n2. Напишите 'отзывы 123456789' — анализ отзывов.\n3. Пример артикула: 157065568")
                
                elif text.lower().startswith("отзывы") and len(text.split()) > 1:
                    article = text.split()[1]
                    if article.isdigit():
                        send_msg(user_id, f"🔍 Собираю отзывы по артикулу {article}... ⏳ (до 20 секунд)")
                        reviews_data = parse_reviews(article)
                        if reviews_data:
                            msg = f"📊 *Анализ отзывов (арт. {article})*\n"
                            msg += f"📝 Всего отзывов: {reviews_data['total']}\n"
                            msg += f"⭐ Средний рейтинг: {reviews_data['avg_rating']}\n\n"
                            
                            if reviews_data['positive']:
                                msg += "✅ *Частые плюсы:*\n"
                                for word, count in reviews_data['positive'].items():
                                    msg += f"   • {word} — {count} раз(а)\n"
                            else:
                                msg += "✅ Явных плюсов не найдено.\n"
                            
                            if reviews_data['negative']:
                                msg += "\n⚠️ *Частые минусы:*\n"
                                for word, count in reviews_data['negative'].items():
                                    msg += f"   • {word} — {count} раз(а)\n"
                            else:
                                msg += "\n⚠️ Явных минусов не найдено.\n"
                            
                            msg += f"\n📌 Топ-10 слов в отзывах:\n"
                            for word, count in list(reviews_data['top_words'].items())[:10]:
                                msg += f"   • {word} — {count}\n"
                            
                            send_msg(user_id, msg)
                        else:
                            send_msg(user_id, "❌ Не удалось загрузить отзывы. Проверьте артикул или попробуйте позже.")
                    else:
                        send_msg(user_id, "❌ Артикул должен быть числом. Пример: отзывы 61472739")
                
                elif text.isdigit():
                    send_msg(user_id, f"🔍 Анализирую артикул {text}... ⏳")
                    data = parse_wb_product(text)
                    if data:
                        product = data['product']
                        comps = data['competitors']
                        analysis = analyze_product(product, comps)
                        
                        msg = f"📦 *Товар:* {product['name'][:60]}...\n"
                        msg += f"💰 *Цена:* {product['price']} ₽"
                        if analysis:
                            if analysis['price_diff'] > 0:
                                msg += f" (🔺 на {analysis['price_diff']}% ДОРОЖЕ рынка, средняя {analysis['avg_price']} ₽)"
                            else:
                                msg += f" (🔻 на {abs(analysis['price_diff'])}% ДЕШЕВЛЕ рынка, средняя {analysis['avg_price']} ₽)"
                        msg += "\n"
                        
                        msg += f"⭐ *Рейтинг:* {product['rating']}"
                        if analysis:
                            if analysis['rating_diff'] > 0:
                                msg += f" (🟢 на {analysis['rating_diff']}% ВЫШЕ рынка, средний {analysis['avg_rating']})"
                            else:
                                msg += f" (🔴 на {abs(analysis['rating_diff'])}% НИЖЕ рынка, средний {analysis['avg_rating']})"
                        msg += "\n"
                        
                        msg += f"💬 *Отзывов:* {product['feedbacks']}"
                        if analysis:
                            if analysis['feedbacks_diff'] > 0:
                                msg += f" (🟢 на {analysis['feedbacks_diff']}% БОЛЬШЕ рынка, среднее {analysis['avg_feedbacks']})"
                            else:
                                msg += f" (🔴 на {abs(analysis['feedbacks_diff'])}% МЕНЬШЕ рынка, среднее {analysis['avg_feedbacks']})"
                        msg += "\n\n"
                        
                        if analysis:
                            strengths = []
                            weaknesses = []
                            if analysis['rating_diff'] > 5:
                                strengths.append(f"✅ Высокий рейтинг (+{analysis['rating_diff']:.1f}%)")
                            elif analysis['rating_diff'] < -5:
                                weaknesses.append(f"⚠️ Низкий рейтинг ({analysis['rating_diff']:.1f}%)")
                            
                            if analysis['feedbacks_diff'] > 10:
                                strengths.append(f"✅ Много отзывов (+{analysis['feedbacks_diff']:.1f}%)")
                            elif analysis['feedbacks_diff'] < -10:
                                weaknesses.append(f"⚠️ Мало отзывов ({analysis['feedbacks_diff']:.1f}%)")
                            
                            if analysis['price_diff'] < -5:
                                strengths.append(f"✅ Привлекательная цена (-{abs(analysis['price_diff']):.1f}%)")
                            elif analysis['price_diff'] > 10:
                                weaknesses.append(f"⚠️ Высокая цена (+{analysis['price_diff']:.1f}%)")
                            
                            if strengths:
                                msg += "🌟 *Сильные стороны:*\n" + "\n".join(strengths) + "\n\n"
                            if weaknesses:
                                msg += "⚠️ *Слабые стороны:*\n" + "\n".join(weaknesses) + "\n\n"
                        
                        msg += "🏆 *Конкуренты (топ-5):*\n"
                        for i, comp in enumerate(comps, 1):
                            msg += f"{i}. {comp['name'][:40]}... — {comp['price']} ₽ (⭐{comp['rating']}, {comp['feedbacks']} отзывов)\n"
                        
                        send_msg(user_id, msg)
                    else:
                        send_msg(user_id, "❌ Не удалось найти товар. Проверьте артикул или попробуйте позже.")
                else:
                    send_msg(user_id, "ℹ️ Отправьте мне артикул товара (цифры) или напишите 'помощь'.")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    traceback.print_exc()
    sys.exit(1)
