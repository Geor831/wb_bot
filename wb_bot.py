import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import requests
import json

# ===== ВАШИ ДАННЫЕ =====
VK_TOKEN = "vk1.a.7Y36GRUm05bC_M1LIerMlh-D2Bxhsy_FKyXH5IegUNL-KSnO8ZnwW66YKCXu0TPbl3Di7j4OadVzM2xssg5zxWdspA2oeXwkQw0ntukuaiQHajCT2mmYkslpUlkiwU_VbjJk86Wm5wi1o2PtxCY2thGE26p7o0KhgGdRB_CqFKx4m7bqPPetaocQkDSzh5mqRad0UfAAVa-UcjmADRQ6ag"
GROUP_ID = 228196102
# =======================

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
                "name": product.get('name'),
                "price": product.get('sizes', [{}])[0].get('price', {}).get('product', 0) / 100,
                "rating": product.get('rating', 0),
                "feedbacks": product.get('feedbacks', 0),
            },
            "competitors": competitors[:5]
        }
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return None

def send_msg(user_id, message):
    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=0
    )

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
                send_msg(user_id, "👋 Привет! Я WB.Analytics — AI-помощник для селлеров Wildberries.\nОтправь мне артикул товара, и я найду его конкурентов.")
            elif text.isdigit():
                send_msg(user_id, f"🔍 Анализирую артикул {text}...")
                data = parse_wb_product(text)
                if data:
                    msg = f"📦 Товар: {data['product']['name'][:50]}...\n💰 Цена: {data['product']['price']} ₽\n⭐ Рейтинг: {data['product']['rating']}\n💬 Отзывов: {data['product']['feedbacks']}\n\n"
                    msg += "🏆 Конкуренты (топ-5):\n"
                    for i, comp in enumerate(data['competitors'], 1):
                        msg += f"{i}. {comp['name'][:40]}... — {comp['price']} ₽ (⭐{comp['rating']}, {comp['feedbacks']} отзывов)\n"
                    send_msg(user_id, msg)
                else:
                    send_msg(user_id, "❌ Не удалось найти товар. Проверьте артикул.")
            else:
                send_msg(user_id, "ℹ️ Отправьте мне артикул товара (цифры) или напишите 'начать'.")
