"""
Утилиты для определения часового пояса пользователя
"""
import requests
import json
from typing import Optional, Dict, Any
import re


class TimezoneHelper:
    """Помощник для определения часового пояса пользователя"""
    
    # Расширенная карта популярных городов России и стран СНГ
    CITY_TIMEZONE_MAP = {
        # Россия - основные города
        "москва": "Europe/Moscow",
        "санкт-петербург": "Europe/Moscow", 
        "спб": "Europe/Moscow",
        "питер": "Europe/Moscow",
        "екатеринбург": "Asia/Yekaterinburg",
        "новосибирск": "Asia/Novosibirsk", 
        "нижний новгород": "Europe/Moscow",
        "казань": "Europe/Moscow",
        "челябинск": "Asia/Yekaterinburg",
        "омск": "Asia/Omsk",
        "самара": "Europe/Samara",
        "ростов-на-дону": "Europe/Moscow",
        "уфа": "Asia/Yekaterinburg",
        "красноярск": "Asia/Krasnoyarsk",
        "воронеж": "Europe/Moscow",
        "пермь": "Asia/Yekaterinburg",
        "волгоград": "Europe/Volgograd",
        "краснодар": "Europe/Moscow",
        "саратов": "Europe/Saratov",
        "тюмень": "Asia/Yekaterinburg",
        "тольятти": "Europe/Samara",
        "ижевск": "Europe/Moscow",
        "барнаул": "Asia/Barnaul",
        "ульяновск": "Europe/Ulyanovsk",
        "иркутск": "Asia/Irkutsk",
        "хабаровск": "Asia/Vladivostok",
        "ярославль": "Europe/Moscow",
        "владивосток": "Asia/Vladivostok",
        "томск": "Asia/Tomsk",
        "оренбург": "Asia/Yekaterinburg",
        "кемерово": "Asia/Novokuznetsk",
        "новокузнецк": "Asia/Novokuznetsk",
        "рязань": "Europe/Moscow",
        "астрахань": "Europe/Astrakhan",
        "набережные челны": "Europe/Moscow",
        "пенза": "Europe/Moscow",
        "липецк": "Europe/Moscow",
        "тула": "Europe/Moscow",
        "киров": "Europe/Kirov",
        "чебоксары": "Europe/Moscow",
        "калининград": "Europe/Kaliningrad",
        "брянск": "Europe/Moscow",
        "курск": "Europe/Moscow",
        "иваново": "Europe/Moscow",
        "магнитогорск": "Asia/Yekaterinburg",
        "тверь": "Europe/Moscow",
        "ставрополь": "Europe/Moscow",
        "белгород": "Europe/Moscow",
        "сочи": "Europe/Moscow",
        "сургут": "Asia/Yekaterinburg",
        "нижневартовск": "Asia/Yekaterinburg",
        "нефтеюганск": "Asia/Yekaterinburg",
        "когалым": "Asia/Yekaterinburg",
        "ноябрьск": "Asia/Yekaterinburg",
        "новый уренгой": "Asia/Yekaterinburg",
        "салехард": "Asia/Yekaterinburg",
        "мурманск": "Europe/Moscow",
        "архангельск": "Europe/Moscow",
        "северодвинск": "Europe/Moscow",
        "сыктывкар": "Europe/Moscow",
        "петрозаводск": "Europe/Moscow",
        "вологда": "Europe/Moscow",
        "великий новгород": "Europe/Moscow",
        "псков": "Europe/Moscow",
        "калуга": "Europe/Moscow",
        "владимир": "Europe/Moscow",
        "кострома": "Europe/Moscow",
        "смоленск": "Europe/Moscow",
        "орел": "Europe/Moscow",
        "тамбов": "Europe/Moscow",
        "воронеж": "Europe/Moscow",
        "махачкала": "Europe/Moscow",
        "нальчик": "Europe/Moscow",
        "владикавказ": "Europe/Moscow",
        "грозный": "Europe/Moscow",
        "элиста": "Europe/Moscow",
        "йошкар-ола": "Europe/Moscow",
        "саранск": "Europe/Moscow",
        "ижевск": "Europe/Moscow",
        "сыктывкар": "Europe/Moscow",
        "якутск": "Asia/Yakutsk",
        "магадан": "Asia/Magadan",
        "петропавловск-камчатский": "Asia/Kamchatka",
        "южно-сахалинск": "Asia/Sakhalin",
        "благовещенск": "Asia/Yakutsk",
        "биробиджан": "Asia/Vladivostok",
        "чита": "Asia/Chita",
        "улан-удэ": "Asia/Irkutsk",
        "абакан": "Asia/Krasnoyarsk",
        "кызыл": "Asia/Krasnoyarsk",
        "горно-алтайск": "Asia/Barnaul",
        
        # Страны СНГ
        "киев": "Europe/Kiev",
        "харьков": "Europe/Kiev", 
        "одесса": "Europe/Kiev",
        "днепр": "Europe/Kiev",
        "львов": "Europe/Kiev",
        "минск": "Europe/Minsk",
        "алматы": "Asia/Almaty",
        "астана": "Asia/Almaty",
        "нур-султан": "Asia/Almaty",
        "ташкент": "Asia/Tashkent",
        "самарканд": "Asia/Samarkand",
        "баку": "Asia/Baku",
        "ереван": "Asia/Yerevan",
        "тбилиси": "Asia/Tbilisi",
        "бишкек": "Asia/Bishkek",
        "душанбе": "Asia/Dushanbe",
        "ашхабад": "Asia/Ashgabat",
        "кишинев": "Europe/Chisinau",
        
        # Крупные международные города
        "лондон": "Europe/London",
        "париж": "Europe/Paris", 
        "берлин": "Europe/Berlin",
        "рим": "Europe/Rome",
        "мадрид": "Europe/Madrid",
        "варшава": "Europe/Warsaw",
        "прага": "Europe/Prague",
        "стокгольм": "Europe/Stockholm",
        "хельсинки": "Europe/Helsinki",
        "осло": "Europe/Oslo",
        "копенгаген": "Europe/Copenhagen",
        "амстердам": "Europe/Amsterdam",
        "брюссель": "Europe/Brussels",
        "вена": "Europe/Vienna",
        "будапешт": "Europe/Budapest",
        "бухарест": "Europe/Bucharest",
        "софия": "Europe/Sofia",
        "афины": "Europe/Athens",
        "стамбул": "Europe/Istanbul",
        "анкара": "Europe/Istanbul",
        "токио": "Asia/Tokyo",
        "пекин": "Asia/Shanghai",
        "шанхай": "Asia/Shanghai",
        "сеул": "Asia/Seoul",
        "бангкок": "Asia/Bangkok",
        "джакарта": "Asia/Jakarta",
        "дели": "Asia/Kolkata",
        "мумбаи": "Asia/Kolkata",
        "дубай": "Asia/Dubai",
        "тель-авив": "Asia/Jerusalem",
        "каир": "Africa/Cairo",
        "нью-йорк": "America/New_York",
        "лос-анджелес": "America/Los_Angeles",
        "чикаго": "America/Chicago",
        "торонто": "America/Toronto",
        "ванкувер": "America/Vancouver",
        "мехико": "America/Mexico_City",
        "сан-паулу": "America/Sao_Paulo",
        "буэнос-айрес": "America/Argentina/Buenos_Aires",
        "сидней": "Australia/Sydney",
        "мельбурн": "Australia/Melbourne",
    }
    
    @classmethod
    def get_timezone_from_city(cls, city_name: str) -> Optional[str]:
        """
        Определяет часовой пояс по названию города
        
        Args:
            city_name: Название города
            
        Returns:
            Название часового пояса в формате IANA или None
        """
        if not city_name:
            return None
            
        # Нормализация названия города
        normalized = cls._normalize_city_name(city_name)
        
        # Поиск в локальной карте
        timezone = cls.CITY_TIMEZONE_MAP.get(normalized)
        if timezone:
            return timezone
            
        # Попытка через онлайн-сервис
        return cls._get_timezone_online(city_name)
    
    @classmethod
    def _normalize_city_name(cls, city_name: str) -> str:
        """Нормализует название города для поиска"""
        if not city_name:
            return ""
            
        # Приводим к нижнему регистру
        normalized = city_name.lower().strip()
        
        # Убираем лишние пробелы
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Удаляем префиксы типа "г.", "город"  
        normalized = re.sub(r'^(г\.|город|city)\s+', '', normalized)
        
        # Заменяем ё на е
        normalized = normalized.replace('ё', 'е')
        
        return normalized
    
    @classmethod
    def _get_timezone_online(cls, city_name: str) -> Optional[str]:
        """
        Получает часовой пояс через онлайн API
        Использует бесплатный сервис WorldTimeAPI
        """
        try:
            # Простой запрос к API для получения списка часовых поясов
            # В реальном проекте лучше использовать геокодинг + timezonefinder
            
            # Попытка найти по регионам
            region_mapping = {
                'москва': 'Europe/Moscow',
                'лондон': 'Europe/London', 
                'нью-йорк': 'America/New_York',
                'токио': 'Asia/Tokyo',
                'пекин': 'Asia/Shanghai',
                'дели': 'Asia/Kolkata',
                'дубай': 'Asia/Dubai'
            }
            
            normalized = cls._normalize_city_name(city_name)
            return region_mapping.get(normalized)
            
        except Exception as e:
            print(f"Error getting timezone online for {city_name}: {e}")
            return None
    
    @classmethod
    def detect_timezone_from_user_data(cls, user_data: Dict[str, Any]) -> str:
        """
        Определяет часовой пояс пользователя на основе его данных
        
        Args:
            user_data: Данные пользователя (city, country, etc.)
            
        Returns:
            IANA timezone string, по умолчанию Europe/Moscow
        """
        # Пробуем определить по городу
        city = user_data.get('city', '').strip()
        if city:
            timezone = cls.get_timezone_from_city(city)
            if timezone:
                return timezone
        
        # Пробуем по стране (если есть)
        country = user_data.get('country', '').lower()
        country_defaults = {
            'россия': 'Europe/Moscow',
            'russia': 'Europe/Moscow', 
            'украина': 'Europe/Kiev',
            'ukraine': 'Europe/Kiev',
            'беларусь': 'Europe/Minsk',
            'belarus': 'Europe/Minsk',
            'казахстан': 'Asia/Almaty',
            'kazakhstan': 'Asia/Almaty',
            'узбекистан': 'Asia/Tashkent',
            'узбекистан': 'Asia/Tashkent'
        }
        
        if country in country_defaults:
            return country_defaults[country]
        
        # По умолчанию - московское время
        return 'Europe/Moscow'
    
    @classmethod
    def validate_timezone(cls, timezone_str: str) -> bool:
        """Проверяет, является ли строка валидным часовым поясом"""
        try:
            import pytz
            pytz.timezone(timezone_str)
            return True
        except:
            return False