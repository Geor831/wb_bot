import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import requests
import json
import sys
import traceback

# ===== ВАШИ ДАННЫЕ =====
VK_TOKEN = "vk1.a.wOAyfLk_ftARYpMVGdnWS1Gy7V0cUArWt_4MZvKZnGHInrstPt_y2dT5B14LjIsRis7OTLWD12LsEcNoPW-O_C8_zB0BfaA2zeW5OyamxxbzeD7VrIoAhsVwaPXmK6uBroTD6_2XnaGUzS_SW0l29QjUmmVgmczJfTQnhnk6l4WsdwFEXDrNawF9osrsjqdO5XHjjNTUSWmnAlpvyt4ouA"
GROUP_ID = 228196102
# ======================================

def parse_wb_product(article):
    try:
        detail_url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={article}"
        detail_response = requests.get(detail_url)
        detail_data = detail_response.json()
        if not detail_data.get('data', {}).get('products'):
            return None
        product = detail_data['data']['products'][0]
        search_query = product.get('name', '').split('/')[0].strip()
        search_url = f"https://search.wb.ru/exactmatch/ru/common/v18/search?appType=1&curr=rub&lang=ru&page=1&query={search_query}&resultset=catalog&sort=popular&spp=30"
        search_response = requests.get(search_url)
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
                "seller": product.get('supplier', ''),
            },
            "competitors": competitors[:5]
        }
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return None

def analyze_product(product, competitors):
    """Анализирует товар относительно конкурентов и возвращает процентные отклонения"""
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
                    send_msg(user_id, "👋 Привет! Я WB.Analytics — аналитик конкурентов.\nОтправь мне артикул товара, и я покажу его плюсы и минусы относительно рынка.\n\n📌 Команды:\n• артикул — анализ товара\n• помощь — список команд")
                
                elif text.lower() == "помощь":
                    send_msg(user_id, "📖 *Помощь по боту*\n\n1. Отправьте артикул Wildberries (число) — я проанализирую товар и конкурентов.\n2. Оценка: покажу, на сколько % ваш товар дороже/дешевле, выше/ниже рейтинг и т.д.\n3. Сильные и слабые стороны — определю автоматически.\n\nПример артикула: 157065568")
                
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
                        send_msg(user_id, "❌ Не удалось найти товар. Проверьте артикул.")
                else:
                    send_msg(user_id, "ℹ️ Отправьте мне артикул товара (цифры) или напишите 'помощь'.")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    traceback.print_exc()
    sys.exit(1)
