import streamlit as st
import os
import openai
import pandas as pd
from datetime import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re


# Set page config
st.set_page_config(
    page_title="Alligator.tour - Travel Assistant",
    page_icon="🧳",
    layout="wide"
)

# Custom CSS (unchanged)
st.markdown("""
<style>
/* Make the sidebar background white */
[data-testid="stSidebar"] {
    background-color: white;
}

/* Optional: Adjust text colors for better contrast on white background */
[data-testid="stSidebar"] .stMarkdown {
    color: #333333;
}

/* Make sure dropdown menus have good contrast */
[data-testid="stSidebar"] .stSelectbox label {
    color: #333333;
}
</style>
""", unsafe_allow_html=True)

# Initialize OpenAI API
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Language support
SUPPORTED_LANGUAGES = {
    "en": "English",
    "de": "German",
    "uk": "Ukrainian",
    "ru": "Russian",
    "ro": "Romanian"
}

# Translations for UI elements
UI_TRANSLATIONS = {
    "en": {
        "title": "Talk to your Travel Assistant 🌎",
        "subtitle": "Ask me about destinations, travel tips, or help planning your next adventure!",
        "input_placeholder": "Type your travel question here...",
        "sidebar_title": "Your Ultimate Travel Companion",
        "popular_destinations": "Popular Destinations",
        "welcome_message": """👋 Hello! I'm your Alligator.tour travel assistant!

I'm here to help you plan an amazing vacation experience. 

✨ Where are you thinking of traveling to? Or if you're not sure yet, I'd be happy to suggest some fantastic destinations based on your interests!"""
    },
    "de": {
        "title": "Sprich mit deinem Reiseassistenten 🌎",
        "subtitle": "Frag mich nach Reisezielen, Reisetipps oder Hilfe bei der Planung deines nächsten Abenteuers!",
        "input_placeholder": "Gib deine Reisefrage hier ein...",
        "sidebar_title": "Dein ultimativer Reisebegleiter",
        "popular_destinations": "Beliebte Reiseziele",
        "welcome_message": """👋 Hallo! Ich bin dein Alligator.tour Reiseassistent!

Ich bin hier, um dir bei der Planung eines tollen Urlaubserlebnisses zu helfen.

✨ Wohin möchtest du reisen? Oder wenn du dir noch nicht sicher bist, kann ich dir gerne einige fantastische Reiseziele basierend auf deinen Interessen vorschlagen!"""
    },
    "uk": {
        "title": "Поговоріть зі своїм туристичним асистентом 🌎",
        "subtitle": "Запитайте мене про напрямки, поради щодо подорожей або допомогу у плануванні вашої наступної пригоди!",
        "input_placeholder": "Введіть своє питання про подорож тут...",
        "sidebar_title": "Ваш ідеальний компаньйон для подорожей",
        "popular_destinations": "Популярні напрямки",
        "welcome_message": """👋 Привіт! Я ваш туристичний асистент Alligator.tour!

Я тут, щоб допомогти вам спланувати чудову відпустку.

✨ Куди ви думаєте поїхати? Або якщо ви ще не впевнені, я можу запропонувати фантастичні напрямки на основі ваших інтересів!"""
    },
    "ru": {
        "title": "Поговорите со своим туристическим ассистентом 🌎",
        "subtitle": "Спросите меня о направлениях, советах по путешествиям или помощи в планировании вашего следующего приключения!",
        "input_placeholder": "Введите свой вопрос о путешествии здесь...",
        "sidebar_title": "Ваш идеальный компаньон для путешествий",
        "popular_destinations": "Популярные направления",
        "welcome_message": """👋 Привет! Я ваш туристический ассистент Alligator.tour!

Я здесь, чтобы помочь вам спланировать замечательный отпуск.

✨ Куда вы думаете поехать? Или если вы еще не уверены, я могу предложить фантастические направления на основе ваших интересов!"""
    },
    "ro": {
        "title": "Vorbește cu asistentul tău de călătorie 🌎",
        "subtitle": "Întreabă-mă despre destinații, sfaturi de călătorie sau ajutor pentru planificarea următoarei tale aventuri!",
        "input_placeholder": "Tastează întrebarea ta despre călătorie aici...",
        "sidebar_title": "Companionul tău ultim de călătorie",
        "popular_destinations": "Destinații populare",
        "welcome_message": """👋 Salut! Sunt asistentul tău de călătorie Alligator.tour!

Sunt aici pentru a te ajuta să planifici o experiență de vacanță uimitoare.

✨ Unde te gândești să călătorești? Sau dacă nu ești încă sigur, aș fi bucuros să îți sugerez câteva destinații fantastice bazate pe interesele tale!"""
    }
}

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'user_info' not in st.session_state:
    st.session_state.user_info = {
        "name": "Not provided",  # Set a default value
        "contact": None,
        "destination": "Not specified",  # Set a default value
        "travel_dates": None,
        "interests": [],
        "budget": None,
        "language": "en"  # Default language is English
    }

if 'contact_requested' not in st.session_state:
    st.session_state.contact_requested = False

if 'contact_saved' not in st.session_state:
    st.session_state.contact_saved = False

# Initialize with welcome message if no messages exist
if len(st.session_state.messages) == 0:
    lang = st.session_state.user_info["language"]
    st.session_state.messages.append(
        {"role": "assistant", "content": UI_TRANSLATIONS[lang]["welcome_message"]}
    )

# Language detection
def detect_language(text):
    """Detect the language of the input text using OpenAI"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a language detector. Output only a two-letter language code from this list: en, de, uk, ru, ro."},
                {"role": "user", "content": f"Detect the language of this text and respond with only the language code: {text}"}
            ],
            temperature=0.1,
            max_tokens=10
        )
        detected_lang = response.choices[0].message["content"].strip().lower()
        
        # Make sure we have a supported language
        if detected_lang in SUPPORTED_LANGUAGES:
            return detected_lang
        return "en"  # Default to English if detection fails
    except Exception as e:
        print(f"Error detecting language: {e}")
        return "en"  # Default to English on error

# Email extraction using regex
def extract_email(message):
    # More permissive email pattern that should work with any character set
    email_pattern = r'[^\s@]+@[^\s@]+\.[^\s@]+'
    email_match = re.search(email_pattern, message)
    if email_match:
        email = email_match.group(0).strip(',.!?;:()')
        print(f"Found email with permissive pattern: {email}")
        return email
    return None

# Helper function to extract travel information from messages
def extract_travel_info(message):
    message_lower = message.lower()
    print(f"Extracting info from: {message}")
    
    # Extract destination
    countries = extract_countries(message)
    if countries:
        st.session_state.user_info["destination"] = countries[0].capitalize()
        print(f"Set destination to: {countries[0].capitalize()}")
    
    # Extract contact info - be more aggressive
    # First check if it looks like just a phone number by itself
    if not st.session_state.user_info["contact"] and message.strip().isdigit() and len(message.strip()) >= 6:
        st.session_state.user_info["contact"] = message.strip()
        print(f"Found raw phone number: {message.strip()}")
        success = save_contact_to_sheet()
        print(f"Save contact success: {success}")
    else:
        # Try to extract email
        email = extract_email(message)
        if email and not st.session_state.user_info["contact"]:
            st.session_state.user_info["contact"] = email
            print(f"Found email: {email}")
            success = save_contact_to_sheet()
            print(f"Save contact success: {success}")
        else:
            # Try to extract phone with better pattern matching
            phone = extract_phone(message)
            if phone and not st.session_state.user_info["contact"]:
                st.session_state.user_info["contact"] = phone
                print(f"Found phone: {phone}")
                success = save_contact_to_sheet()
                print(f"Save contact success: {success}")
    
    print(f"Updated user_info: {st.session_state.user_info}")

# Improved destinations extraction
def extract_countries(message):
    message_lower = message.lower()
    print(f"Checking for destinations in: {message_lower}")
    
    # Add more destinations
    common_destinations = [
        "france", "frankreich", "франція", "франция", "franța",
        "italy", "italien", "італія", "италия", "italia",
        "spain", "spanien", "іспанія", "испания", "spania",
        "greece", "griechenland", "греція", "греция", "grecia",
        "japan", "japan", "японія", "япония", "japonia",
        "thailand", "thailand", "таїланд", "таиланд", "tailanda",
        "australia", "australien", "австралія", "австралия", "australia",
        "canada", "kanada", "канада", "канада", "canada",
        "mexico", "mexiko", "мексика", "мексика", "mexic",
        "brazil", "brasilien", "бразилія", "бразилия", "brazilia",
        "egypt", "ägypten", "єгипет", "египет", "egipt",
        "turkey", "türkei", "туреччина", "турция", "turcia",
        "germany", "deutschland", "німеччина", "германия", "germania",
        "uk", "großbritannien", "великобританія", "великобритания", "marea britanie",
        "ireland", "irland", "ірландія", "ирландия", "irlanda",
        "china", "china", "китай", "китай", "china",
        "india", "indien", "індія", "индия", "india",
        "morocco", "marokko", "марокко", "марокко", "maroc",
        "south africa", "südafrika", "південна африка", "южная африка", "africa de sud",
        "peru", "peru", "перу", "перу", "peru",
        "argentina", "argentinien", "аргентина", "аргентина", "argentina",
        "chile", "chile", "чилі", "чили", "chile",
        "vietnam", "vietnam", "в'єтнам", "вьетнам", "vietnam",
        "cambodia", "kambodscha", "камбоджа", "камбоджа", "cambodgia",
        "singapore", "singapur", "сінгапур", "сингапур", "singapore",
        "indonesia", "indonesien", "індонезія", "индонезия", "indonezia",
        "bali", "bali", "балі", "бали", "bali",
        "iceland", "island", "ісландія", "исландия", "islanda",
        "sweden", "schweden", "швеція", "швеция", "suedia",
        "norway", "norwegen", "норвегія", "норвегия", "norvegia",
        "denmark", "dänemark", "данія", "дания", "danemarca",
        "netherlands", "niederlande", "нідерланди", "нидерланды", "țările de jos",
        "portugal", "portugal", "португалія", "португалия", "portugalia",
        "croatia", "kroatien", "хорватія", "хорватия", "croația",
        "switzerland", "schweiz", "швейцарія", "швейцария", "elveția",
        "austria", "österreich", "австрія", "австрия", "austria",
        "new zealand", "neuseeland", "нова зеландія", "новая зеландия", "noua zeelandă",
        "fiji", "fidschi", "фіджі", "фиджи", "fiji",
        "costa rica", "costa rica", "коста-ріка", "коста-рика", "costa rica",
        "usa", "usa", "сша", "сша", "sua",
        "united states", "vereinigte staaten", "сполучені штати", "соединенные штаты", "statele unite",
        "ukraine", "ukraine", "україна", "украина", "ucraina",
        "dnipro", "dnipro", "дніпро", "днепр", "nipru",
        "kyiv", "kiew", "київ", "киев", "kiev",
        "odessa", "odessa", "одеса", "одесса", "odesa",
        "lviv", "lemberg", "львів", "львов", "liov",
        # Add specific cities
        "rome", "rom", "рим", "рим", "roma",
        "paris", "paris", "париж", "париж", "paris",
        "london", "london", "лондон", "лондон", "londra",
        "tokyo", "tokio", "токіо", "токио", "tokyo",
        "barcelona", "barcelona", "барселона", "барселона", "barcelona",
        "new york", "new york", "нью-йорк", "нью-йорк", "new york",
        "los angeles", "los angeles", "лос-анджелес", "лос-анджелес", "los angeles"
    ]
    
    found_destinations = []
    for destination in common_destinations:
        if destination in message_lower:
            found_destinations.append(destination)
            print(f"Matched destination: {destination}")
    
    # If not found directly, check if the user's message looks like just a destination
    if not found_destinations and len(message.split()) <= 2:
        # Check if it's a proper noun (capitalized word)
        words = message.split()
        for word in words:
            cleaned_word = word.strip(',.:;!?')
            if cleaned_word and cleaned_word[0].isupper() and len(cleaned_word) > 3:
                found_destinations.append(cleaned_word.lower())
                print(f"Found potential destination from capitalized word: {cleaned_word}")
                break
            
    return found_destinations

# Improved phone extraction
def extract_phone(message):
    # First try to find formatted phone numbers
    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
    phone_match = re.search(phone_pattern, message)
    if phone_match:
        return phone_match.group(0)
    
    # Look for any sequence of digits
    digits_only = ''.join(c for c in message if c.isdigit())
    if len(digits_only) >= 6:  # More permissive - any 6+ digit sequence
        return digits_only
    
    return None

def save_contact_to_sheet():
    """Function to save contact details to Google Sheets using Streamlit secrets"""
    if not st.session_state.user_info["contact"]:
        print("No contact to save")
        return False
    
    try:
        # Ensure we have values for all fields
        destination = st.session_state.user_info.get("destination")
        if not destination or destination == "None":
            # Logic to find destination from chat history (keep your existing code)
            pass
        
        # Prepare data to save
        data = {
            "name": st.session_state.user_info.get("name") or "Not provided",
            "contact": st.session_state.user_info["contact"],
            "destination": destination or "Not specified",
            "interests": ", ".join(st.session_state.user_info.get("interests", [])) or "Not specified",
            "budget": st.session_state.user_info.get("budget") or "Not specified",
            "language": st.session_state.user_info.get("language") or "en",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        print(f"Data to save: {data}")
        
        # Use Google Sheets with credentials from Streamlit secrets
        import json
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Parse the JSON string from secrets
        google_creds_json = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        credentials = ServiceAccountCredentials.from_service_account_info(google_creds_json, scope)
        client = gspread.authorize(credentials)
        
        # Get spreadsheet ID from URL (you can also store this in secrets)
        sheet_url = "https://docs.google.com/spreadsheets/d/1u0oWbOWXJaPwKfBXBrebc67s0PAz1tgCh7Og_Neaofk/edit?gid=0#gid=0"
        sheet_id = st.secrets.get("SHEET_ID", "1u0oWbOWXJaPwKfBXBrebc67s0PAz1tgCh7Og_Neaofk")
        
        # Open sheet and add row
        sheet = client.open_by_key(sheet_id).sheet1
        
        # Add the row with all data
        row_data = [
            data["name"],
            data["contact"],
            data["destination"],
            data["interests"],
            data["budget"],
            data["language"],
            data["timestamp"]
        ]
        
        print(f"Row data: {row_data}")
        sheet.append_row(row_data)
        print(f"Successfully saved contact data to Google Sheet")
        
        st.session_state.contact_saved = True
        return True
        
    except Exception as e:
        print(f"Error saving to Google Sheet: {e}")
        # More detailed error trace
        import traceback
        print(traceback.format_exc())
        
        # Try CSV fallback if needed
        try:
            fallback_file = "contact_leads.csv"
            import csv
            file_exists = os.path.exists(fallback_file)
            with open(fallback_file, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Name", "Contact", "Destination", "Interests", "Budget", "Language", "Timestamp"])
                writer.writerow([
                    data["name"],
                    data["contact"],
                    data["destination"],
                    data["interests"],
                    data["budget"],
                    data["language"],
                    data["timestamp"]
                ])
            print(f"Saved to local CSV file: {fallback_file}")
        except Exception as csv_err:
            print(f"Error saving to CSV: {str(csv_err)}")
        return False

def should_request_contact():
    # Check if we've collected enough info and should ask for contact
    if st.session_state.contact_requested or st.session_state.contact_saved:
        return False
    
    # Always request contact after a few messages, even if no destination yet
    # This ensures we always collect contact info
    if len(st.session_state.messages) >= 2 and not st.session_state.user_info["contact"]:
        print("Setting contact_requested to True")
        st.session_state.contact_requested = True
        return True
    
    return False

def get_system_message():
    # Get the user's current language
    lang = st.session_state.user_info.get("language") or "en"
    
    # Base message localized based on language
    if lang == "en":
        base_message = """You are a friendly and knowledgeable travel agent for Alligator.tour travel agency. 
        Your goal is to help users plan their perfect international trip.
        
        IMPORTANT GUIDELINES:
        
        1. ALWAYS ask targeted questions to understand their needs. For example: "Are you looking for relaxation, adventure, culture, or family fun?"
        
        2. After they mention a destination or show interest, OFFER HELP OPTIONS using this format:
           
           "I'd be happy to help you with your [DESTINATION] trip! What would you like to know about? 
           
           🗺️ Recommended itinerary
           🧳 Packing tips and important documents
           🏨 Accommodation suggestions
           🍽️ Local cuisine recommendations
           🚶 Must-see attractions and activities
           💡 Local customs and travel tips
           💰 Budget advice and money-saving tips"
        
        3. Use plenty of relevant emojis throughout your responses
        
        4. Break up your text into small, digestible paragraphs (2-3 sentences maximum)
        
        5. When providing information, use subheadings and bullet points to organize it
        
        6. Be enthusiastic and conversational
        
        7. ALWAYS ask follow-up questions to better understand their needs at the end of your responses
        
        8. When appropriate, subtly encourage booking through Alligator.tour
        
        9. VERY IMPORTANT: At the end of your responses (especially after providing substantive travel information), ask for the user's contact information like this:
        
           "Would you like a travel specialist to contact you with personalized recommendations for [DESTINATION]? If so, please share your email or phone number."
           
        IMPORTANT: The user is speaking in English. You must respond in English.
        """
    elif lang == "de":
        base_message = """Du bist ein freundlicher und kenntnisreicher Reiseberater für die Alligator.tour Reiseagentur.
        Dein Ziel ist es, Benutzern bei der Planung ihrer perfekten internationalen Reise zu helfen.
        
        WICHTIGE RICHTLINIEN:
        
        1. Stelle IMMER gezielte Fragen, um ihre Bedürfnisse zu verstehen. Zum Beispiel: "Suchst du nach Entspannung, Abenteuer, Kultur oder Familienspaß?"
        
        2. Nachdem sie ein Reiseziel erwähnt haben oder Interesse zeigen, BIETE HILFEOPTIONEN in diesem Format an:
           
           "Ich helfe dir gerne bei deiner Reise nach [REISEZIEL]! Was möchtest du wissen über?
           
           🗺️ Empfohlene Reiseroute
           🧳 Packtipps und wichtige Dokumente
           🏨 Unterkunftsvorschläge
           🍽️ Empfehlungen für lokale Küche
           🚶 Sehenswürdigkeiten und Aktivitäten
           💡 Lokale Bräuche und Reisetipps
           💰 Budgetberatung und Geldsparen"
        
        3. Verwende viele relevante Emojis in deinen Antworten
        
        4. Teile deinen Text in kleine, verdauliche Absätze auf (maximal 2-3 Sätze)
        
        5. Bei der Bereitstellung von Informationen, verwende Unterüberschriften und Aufzählungspunkte
        
        6. Sei begeistert und gesprächig
        
        7. Stelle IMMER Folgefragen, um ihre Bedürfnisse am Ende deiner Antworten besser zu verstehen
        
        8. Wenn es angebracht ist, ermuntere sie subtil, über Alligator.tour zu buchen
        
        9. SEHR WICHTIG: Am Ende deiner Antworten (besonders nach substantiellen Reiseinformationen), frage nach den Kontaktinformationen des Benutzers wie folgt:
        
           "Möchtest du, dass ein Reisespezialist dich mit personalisierten Empfehlungen für [REISEZIEL] kontaktiert? Wenn ja, teile bitte deine E-Mail-Adresse oder Telefonnummer mit."
           
        WICHTIG: Der Benutzer spricht Deutsch. Du musst auf Deutsch antworten.
        """
    elif lang == "uk":
        base_message = """Ви дружелюбний та компетентний туристичний агент агентства Alligator.tour.
        Ваша мета - допомогти користувачам спланувати їхню ідеальну міжнародну подорож.
        
        ВАЖЛИВІ ВКАЗІВКИ:
        
        1. ЗАВЖДИ задавайте цільові питання, щоб зрозуміти їхні потреби. Наприклад: "Ви шукаєте відпочинок, пригоди, культуру чи сімейні розваги?"
        
        2. Після того, як вони згадають пункт призначення або проявлять інтерес, ЗАПРОПОНУЙТЕ ВАРІАНТИ ДОПОМОГИ у такому форматі:
           
           "Я з радістю допоможу вам із поїздкою до [ПУНКТ ПРИЗНАЧЕННЯ]! Що б ви хотіли дізнатися про?
           
           🗺️ Рекомендований маршрут
           🧳 Поради щодо пакування та важливі документи
           🏨 Пропозиції житла
           🍽️ Рекомендації місцевої кухні
           🚶 Обов'язкові пам'ятки та розваги
           💡 Місцеві звичаї та поради для подорожей
           💰 Поради щодо бюджету та економії грошей"
        
        3. Використовуйте багато відповідних емодзі у своїх відповідях
        
        4. Розбивайте текст на невеликі, легкозасвоювані абзаци (максимум 2-3 речення)
        
        5. При наданні інформації використовуйте підзаголовки та маркери
        
        6. Будьте ентузіазними та комунікабельними
        
        7. ЗАВЖДИ ставте уточнюючі запитання, щоб краще зрозуміти їхні потреби в кінці ваших відповідей
        
        8. Коли доречно, тонко заохочуйте бронювання через Alligator.tour
        
        9. ДУЖЕ ВАЖЛИВО: В кінці ваших відповідей (особливо після надання змістовної інформації про подорож), запитайте контактну інформацію користувача таким чином:
        
           "Бажаєте, щоб фахівець з подорожей зв'язався з вами з персоналізованими рекомендаціями для [ПУНКТ ПРИЗНАЧЕННЯ]? Якщо так, будь ласка, поділіться своєю електронною поштою або номером телефону."
           
        ВАЖЛИВО: Користувач говорить українською. Ви повинні відповідати українською.
        """
    elif lang == "ru":
        base_message = """Вы дружелюбный и знающий турагент агентства Alligator.tour.
        Ваша цель - помочь пользователям спланировать их идеальное международное путешествие.
        
        ВАЖНЫЕ УКАЗАНИЯ:
        
        1. ВСЕГДА задавайте целевые вопросы, чтобы понять их потребности. Например: "Вы ищете релаксацию, приключения, культуру или семейное веселье?"
        
        2. После того, как они упомянут место назначения или проявят интерес, ПРЕДЛОЖИТЕ ВАРИАНТЫ ПОМОЩИ в таком формате:
           
           "Я буду рад помочь вам с поездкой в [МЕСТО НАЗНАЧЕНИЯ]! Что бы вы хотели узнать о?
           
           🗺️ Рекомендуемый маршрут
           🧳 Советы по упаковке и важные документы
           🏨 Предложения по проживанию
           🍽️ Рекомендации местной кухни
           🚶 Обязательные достопримечательности и развлечения
           💡 Местные обычаи и советы для путешествий
           💰 Советы по бюджету и экономии денег"
        
        3. Используйте много соответствующих эмодзи в своих ответах
        
        4. Разбивайте текст на небольшие, легкоусвояемые абзацы (максимум 2-3 предложения)
        
        5. При предоставлении информации используйте подзаголовки и маркеры
        
        6. Будьте энтузиастичны и разговорчивы
        
        7. ВСЕГДА задавайте дополнительные вопросы, чтобы лучше понять их потребности в конце ваших ответов
        
        8. Когда уместно, тонко поощряйте бронирование через Alligator.tour
        
        9. ОЧЕНЬ ВАЖНО: В конце ваших ответов (особенно после предоставления существенной информации о путешествии), запрашивайте контактную информацию пользователя следующим образом:
        
           "Хотели бы вы, чтобы специалист по путешествиям связался с вами с персонализированными рекомендациями для [МЕСТО НАЗНАЧЕНИЯ]? Если да, пожалуйста, поделитесь своей электронной почтой или номером телефона."
           
        ВАЖНО: Пользователь говорит на русском языке. Вы должны отвечать на русском.
        """
    elif lang == "ro":
        base_message = """Ești un agent de turism prietenos și competent pentru agenția de turism Alligator.tour.
        Scopul tău este să ajuți utilizatorii să-și planifice călătoria internațională perfectă.
        
        INDICAȚII IMPORTANTE:
        
        1. ÎNTOTDEAUNA pune întrebări specifice pentru a înțelege nevoile lor. De exemplu: "Cauți relaxare, aventură, cultură sau distracție pentru familie?"
        
        2. După ce menționează o destinație sau arată interes, OFERĂ OPȚIUNI DE AJUTOR în acest format:
           
           "Aș fi încântat să te ajut cu călătoria ta în [DESTINAȚIE]! Ce ai dori să știi despre?
           
           🗺️ Itinerar recomandat
           🧳 Sfaturi de împachetare și documente importante
           🏨 Sugestii de cazare
           🍽️ Recomandări de bucătărie locală
           🚶 Atracții și activități de neratat
           💡 Obiceiuri locale și sfaturi de călătorie
           💰 Sfaturi de buget și economisire a banilor"
        
        3. Folosește multe emoji-uri relevante în răspunsurile tale
        
        4. Împarte textul în paragrafe mici, ușor de citit (maximum 2-3 propoziții)
        
        5. Când oferi informații, folosește subtitluri și puncte
        
        6. Fii entuziast și conversațional
        
        7. ÎNTOTDEAUNA pune întrebări suplimentare pentru a înțelege mai bine nevoile lor la sfârșitul răspunsurilor tale
        
        8. Când este potrivit, încurajează subtil rezervarea prin Alligator.tour
        
        9. FOARTE IMPORTANT: La sfârșitul răspunsurilor tale (mai ales după ce ai oferit informații substanțiale despre călătorie), cere informațiile de contact ale utilizatorului astfel:
        
           "Ai dori ca un specialist în călătorii să te contacteze cu recomandări personalizate pentru [DESTINAȚIE]? Dacă da, te rog să împărtășești adresa ta de email sau numărul tău de telefon."
           
        IMPORTANT: Utilizatorul vorbește în română. Trebuie să răspunzi în română.
        """
    
    # Add contact collection if needed
    if should_request_contact():
        # Localized contact request based on language
        if lang == "en":
            contact_request = """
            The user has been engaged in conversation for a while. You MUST include a polite request for their 
            contact information (email or phone) at the end of your response, like this:
            
            "📝 To provide you with personalized travel recommendations, could you please share your email address or phone number?"
            
            This is VERY IMPORTANT. Do NOT forget to include this.
            """
        elif lang == "de":
            contact_request = """
            Der Benutzer ist seit einiger Zeit im Gespräch. Du MUSST am Ende deiner Antwort eine höfliche Anfrage nach seinen 
            Kontaktinformationen (E-Mail oder Telefon) einfügen, wie folgt:
            
            "📝 Um dir personalisierte Reiseempfehlungen geben zu können, könntest du bitte deine E-Mail-Adresse oder Telefonnummer mitteilen?"
            
            Dies ist SEHR WICHTIG. Vergiss NICHT, dies einzufügen.
            """
        elif lang == "uk":
            contact_request = """
            Користувач бере участь у розмові вже деякий час. Ви ПОВИННІ включити ввічливий запит їхньої 
            контактної інформації (електронна пошта або телефон) наприкінці вашої відповіді, наприклад:
            
            "📝 Щоб надати вам персоналізовані рекомендації щодо подорожей, чи не могли б ви поділитися своєю електронною поштою або номером телефону?"
            
            Це ДУЖЕ ВАЖЛИВО. НЕ забудьте включити це.
            """
        elif lang == "ru":
            contact_request = """
            Пользователь участвует в разговоре уже некоторое время. Вы ДОЛЖНЫ включить вежливый запрос их 
            контактной информации (электронная почта или телефон) в конце вашего ответа, например:
            
            "📝 Чтобы предоставить вам персонализированные рекомендации по путешествиям, не могли бы вы поделиться своей электронной почтой или номером телефона?"
            
            Это ОЧЕНЬ ВАЖНО. НЕ забудьте включить это.
            """
        elif lang == "ro":
            contact_request = """
            Utilizatorul a fost implicat în conversație de ceva timp. TREBUIE să incluzi o solicitare politicoasă pentru 
            informațiile lor de contact (email sau telefon) la sfârșitul răspunsului tău, astfel:
            
            "📝 Pentru a-ți oferi recomandări de călătorie personalizate, ai putea să-mi împărtășești adresa ta de email sau numărul tău de telefon?"
            
            Acest lucru este FOARTE IMPORTANT. NU uita să incluzi acest lucru.
            """
        
        base_message += contact_request
    
    # Add current user info context
    base_message += f"\nCurrent user information: {st.session_state.user_info}"
    
    return base_message

def get_response(prompt):
    # Get current language
    lang = st.session_state.user_info.get("language") or "en"
    
    # Prepare the conversation history for the API call
    messages = [{"role": "system", "content": get_system_message()}]
    
    # Add conversation history (excluding system messages)
    for msg in st.session_state.messages:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add the current prompt
    messages.append({"role": "user", "content": prompt})
    
    try:
        # Call the OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=800  # Increased for multilingual responses
        )
        
        response_content = response.choices[0].message["content"]
        
        # Make sure there's a question in the response
        if "?" not in response_content:
            # Add a generic follow-up question based on language
            if lang == "en":
                question = "\n\n✨ What else would you like to know about your travel plans? Do you have any specific interests or preferences for your trip?"
            elif lang == "de":
                question = "\n\n✨ Was möchtest du sonst noch über deine Reisepläne wissen? Hast du bestimmte Interessen oder Vorlieben für deine Reise?"
            elif lang == "uk":
                question = "\n\n✨ Що ще ви хотіли б дізнатися про ваші плани подорожі? У вас є якісь конкретні інтереси чи уподобання для вашої поїздки?"
            elif lang == "ru":
                question = "\n\n✨ Что еще вы хотели бы узнать о ваших планах путешествия? У вас есть какие-то конкретные интересы или предпочтения для вашей поездки?"
            elif lang == "ro":
                question = "\n\n✨ Ce altceva ai dori să știi despre planurile tale de călătorie? Ai interese sau preferințe specifice pentru călătoria ta?"
            else:
                question = "\n\n✨ What else would you like to know about your travel plans?"
                
            response_content += question
        
        # If contact request is needed but missing, add it
        if should_request_contact():
            # Check if there's already a contact request in the response
            contact_phrases = {
                "en": "email or phone",
                "de": "e-mail oder telefon",
                "uk": "електронн",
                "ru": "электронн",
                "ro": "email sau telefon"
            }
            
            if contact_phrases[lang].lower() not in response_content.lower():
                # Add language-specific contact request
                destination = st.session_state.user_info["destination"] or "your trip"
                
                if lang == "en":
                    contact_request = f"\n\n📝 To provide you with personalized recommendations for {destination}, could you please share your email address or phone number?"
                elif lang == "de":
                    contact_request = f"\n\n📝 Um dir personalisierte Empfehlungen für {destination} geben zu können, könntest du bitte deine E-Mail-Adresse oder Telefonnummer mitteilen?"
                elif lang == "uk":
                    contact_request = f"\n\n📝 Щоб надати вам персоналізовані рекомендації щодо {destination}, чи не могли б ви поділитися своєю електронною поштою або номером телефону?"
                elif lang == "ru":
                    contact_request = f"\n\n📝 Чтобы предоставить вам персонализированные рекомендации по {destination}, не могли бы вы поделиться своей электронной почтой или номером телефона?"
                elif lang == "ro":
                    contact_request = f"\n\n📝 Pentru a-ți oferi recomandări personalizate pentru {destination}, ai putea să-mi împărtășești adresa ta de email sau numărul tău de telefon?"
                
                response_content += contact_request
        
        return response_content
    except Exception as e:
        # Error message in appropriate language
        if lang == "en":
            return f"I'm having trouble connecting to our travel database. Please try again or contact Alligator.tour directly. Error: {str(e)}"
        elif lang == "de":
            return f"Ich habe Probleme, eine Verbindung zu unserer Reisedatenbank herzustellen. Bitte versuche es erneut oder kontaktiere Alligator.tour direkt. Fehler: {str(e)}"
        elif lang == "uk":
            return f"У мене виникли проблеми з підключенням до нашої бази даних подорожей. Будь ласка, спробуйте ще раз або зверніться безпосередньо до Alligator.tour. Помилка: {str(e)}"
        elif lang == "ru":
            return f"У меня возникли проблемы с подключением к нашей базе данных путешествий. Пожалуйста, попробуйте еще раз или обратитесь напрямую в Alligator.tour. Ошибка: {str(e)}"
        elif lang == "ro":
            return f"Am probleme cu conectarea la baza noastră de date de călătorie. Te rog să încerci din nou sau să contactezi Alligator.tour direct. Eroare: {str(e)}"
        else:
            return f"Error: {str(e)}"

# Language selector for the sidebar
def language_selector():
    lang = st.session_state.user_info.get("language") or "en"
    
    # Labels for each language in its own language
    language_labels = {
        "en": "English",
        "de": "Deutsch",
        "uk": "Українська",
        "ru": "Русский",
        "ro": "Română"
    }
    
    selected_lang = st.sidebar.selectbox(
        "Language / Sprache / Мова / Язык / Limbă",
        options=list(SUPPORTED_LANGUAGES.keys()),
        format_func=lambda x: language_labels[x],
        index=list(SUPPORTED_LANGUAGES.keys()).index(lang)
    )
    
    # Update language if changed
    if selected_lang != lang:
        st.session_state.user_info["language"] = selected_lang
        # Add a system message about language change
        if len(st.session_state.messages) > 0:
            # Clear existing messages except the first welcome message
            welcome_msg = st.session_state.messages[0]
            st.session_state.messages = [
                {"role": "assistant", "content": UI_TRANSLATIONS[selected_lang]["welcome_message"]}
            ]
        st.rerun() 
# Sidebar
with st.sidebar:
    try:
        st.image("logo.png", width=200)
    except:
        st.title("🐊 Alligator.tour")
    
    # Add language selector
    language_selector()
    
    # Current language
    lang = st.session_state.user_info.get("language") or "en"
    
    st.markdown(f"### {UI_TRANSLATIONS[lang]['sidebar_title']}")
    st.markdown("---")
    
    # Popular destinations
    st.markdown(f"## {UI_TRANSLATIONS[lang]['popular_destinations']}")
    
    destinations = [
        {
            "name": "Bali, Indonesia",
            "image": "bali.png",
            "desc": "Tropical paradise with beaches, temples, and rice terraces"
        },
        {
            "name": "Barcelona, Spain",
            "image": "barcelona.png",
            "desc": "Stunning architecture, Mediterranean beaches, and vibrant culture"
        },
        {
            "name": "Tokyo, Japan",
            "image": "tokyo.png",
            "desc": "Blend of ultramodern and traditional with amazing food"
        }
    ]
    
    # Use Streamlit's native image display rather than HTML
    for dest in destinations:
        st.markdown(f"### {dest['name']}")
        try:
            st.image(dest['image'], use_container_width=True)
            st.markdown(dest['desc'])
        except Exception as e:
            st.error(f"Could not load image: {e}")
            st.markdown(dest['desc'])

# Main content - use translated UI elements
lang = st.session_state.user_info.get("language") or "en"
st.title(UI_TRANSLATIONS[lang]["title"])
st.markdown(UI_TRANSLATIONS[lang]["subtitle"])

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Get user input
user_input = st.chat_input(UI_TRANSLATIONS[lang]["input_placeholder"])

# Process user input
if user_input:
    # Detect language ONLY on the first user message
    if len(st.session_state.messages) == 1:  # Only the initial welcome message exists
        detected_lang = detect_language(user_input)
        if detected_lang != st.session_state.user_info.get("language"):
            st.session_state.user_info["language"] = detected_lang
            print(f"Initial language detection: {detected_lang}")
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Display user message
    with st.chat_message("user"):
        st.write(user_input)
    
    # Extract information from user message
    extract_travel_info(user_input)
    
    # Display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = get_response(user_input)
            st.write(response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
