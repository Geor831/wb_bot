import io
import PyPDF2
import re
from collections import Counter

def extract_text_from_pdf(pdf_bytes):
    """Извлекает текст из PDF-файла"""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Ошибка чтения PDF: {e}")
        return None

def parse_pdf_reviews(pdf_bytes):
    """Анализирует отзывы из PDF"""
    text = extract_text_from_pdf(pdf_bytes)
    if not text:
        return None
    
    # Ищем рейтинг (например, "4,9" или "4.9")
    rating_match = re.search(r'(\d+[,.]\d+)\s*Выбор покупателей', text)
    avg_rating = rating_match.group(1).replace(',', '.') if rating_match else None
    
    # Ищем количество оценок
    count_match = re.search(r'(\d+[\s]?\d*)\s*оценок', text)
    total_ratings = count_match.group(1).replace(' ', '') if count_match else None
    
    # Разбиваем на отзывы (поиск по ключевым словам)
    # Упрощённо: берём весь текст и считаем слова
    words = re.findall(r'\b[а-яёа-я]+\b', text.lower())
    stop_words = {"и", "в", "на", "с", "по", "к", "у", "о", "от", "за", "из", "без", "для", "как", "что", "это", "очень", "был", "но", "только", "ещё", "уже", "все", "всё", "его", "её", "их", "ваш", "наш", "мой", "твой", "так", "вот", "да", "нет", "или", "где", "когда", "потом", "сейчас", "если", "чтобы", "пока", "ведь", "же", "ли", "бы"}
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
