from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import openai
from dotenv import load_dotenv
import re
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import uuid
import uvicorn

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Alligator.tour Travel Assistant")

# Configure CORS to allow embedding in existing website
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your main website domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Language support
SUPPORTED_LANGUAGES = {
    "en": "English",
    "de": "German",
    "uk": "Ukrainian",
    "ru": "Russian",
    "ro": "Romanian"
}

# Default welcome messages for each language
WELCOME_MESSAGES = {
    "en": """👋 Hello! I'm your Alligator.tour travel assistant!

I'm here to help you plan an amazing vacation experience.

✨ Where are you thinking of traveling to? Or if you're not sure yet, I'd be happy to suggest some fantastic destinations based on your interests!""",
    "de": """👋 Hallo! Ich bin dein Alligator.tour Reiseassistent!

Ich bin hier, um dir bei der Planung eines tollen Urlaubserlebnisses zu helfen.

✨ Wohin möchtest du reisen? Oder wenn du dir noch nicht sicher bist, kann ich dir gerne einige fantastische Reiseziele basierend auf deinen Interessen vorschlagen!""",
    "uk": """👋 Привіт! Я ваш туристичний асистент Alligator.tour!

Я тут, щоб допомогти вам спланувати чудову відпустку.

✨ Куди ви думаєте поїхати? Або якщо ви ще не впевнені, я можу запропонувати фантастичні напрямки на основі ваших інтересів!""",
    "ru": """👋 Привет! Я ваш туристический ассистент Alligator.tour!

Я здесь, чтобы помочь вам спланировать замечательный отпуск.

✨ Куда вы думаете поехать? Или если вы еще не уверены, я могу предложить фантастические направления на основе ваших интересов!""",
    "ro": """👋 Salut! Sunt asistentul tău de călătorie Alligator.tour!

Sunt aici pentru a te ajuta să planifici o experiență de vacanță uimitoare.

✨ Unde te gândești să călătorești? Sau dacă nu ești încă sigur, aș fi bucuros să îți sugerez câteva destinații fantastice bazate pe interesele tale!"""
}

# Destination information in different languages
DESTINATIONS = {
    "en": [
        {
            "name": "Bali, Indonesia",
            "description": "Tropical paradise with beaches, temples, and rice terraces",
            "best_time": "April to October"
        },
        {
            "name": "Barcelona, Spain",
            "description": "Stunning architecture, Mediterranean beaches, and vibrant culture",
            "best_time": "May to June, September to October"
        },
        {
            "name": "Tokyo, Japan",
            "description": "Blend of ultramodern and traditional with amazing food",
            "best_time": "March to May, September to November"
        }
    ],
    "de": [
        {
            "name": "Bali, Indonesien",
            "description": "Tropisches Paradies mit Stränden, Tempeln und Reisterrassen",
            "best_time": "April bis Oktober"
        },
        {
            "name": "Barcelona, Spanien",
            "description": "Atemberaubende Architektur, Mittelmeerstrände und lebendige Kultur",
            "best_time": "Mai bis Juni, September bis Oktober"
        },
        {
            "name": "Tokio, Japan",
            "description": "Mischung aus ultramodern und traditionell mit erstaunlichem Essen",
            "best_time": "März bis Mai, September bis November"
        }
    ],
    "uk": [
        {
            "name": "Балі, Індонезія",
            "description": "Тропічний рай з пляжами, храмами та рисовими терасами",
            "best_time": "Квітень - Жовтень"
        },
        {
            "name": "Барселона, Іспанія",
            "description": "Вражаюча архітектура, середземноморські пляжі та яскрава культура",
            "best_time": "Травень - Червень, Вересень - Жовтень"
        },
        {
            "name": "Токіо, Японія",
            "description": "Поєднання ультрасучасного і традиційного з дивовижною їжею",
            "best_time": "Березень - Травень, Вересень - Листопад"
        }
    ],
    "ru": [
        {
            "name": "Бали, Индонезия",
            "description": "Тропический рай с пляжами, храмами и рисовыми террасами",
            "best_time": "Апрель - Октябрь"
        },
        {
            "name": "Барселона, Испания",
            "description": "Потрясающая архитектура, средиземноморские пляжи и яркая культура",
            "best_time": "Май - Июнь, Сентябрь - Октябрь"
        },
        {
            "name": "Токио, Япония",
            "description": "Сочетание ультрасовременного и традиционного с удивительной едой",
            "best_time": "Март - Май, Сентябрь - Ноябрь"
        }
    ],
    "ro": [
        {
            "name": "Bali, Indonezia",
            "description": "Paradis tropical cu plaje, temple și terase de orez",
            "best_time": "Aprilie - Octombrie"
        },
        {
            "name": "Barcelona, Spania",
            "description": "Arhitectură uimitoare, plaje mediteraneene și cultură vibrantă",
            "best_time": "Mai - Iunie, Septembrie - Octombrie"
        },
        {
            "name": "Tokyo, Japonia", 
            "description": "Amestec de ultramodern și tradițional cu mâncare uimitoare",
            "best_time": "Martie - Mai, Septembrie - Noiembrie"
        }
    ]
}

# Pydantic models for request/response validation
class ChatRequest(BaseModel):
    message: str
    lang: str = "en"
    session_id: str = None
    user_info: dict = None

class LanguageRequest(BaseModel):
    lang: str

# Routes
@app.get("/", response_class=HTMLResponse)
async def get_chat_interface(request: Request, lang: str = "uk"):
    """Serve the chat interface page"""
    if lang not in SUPPORTED_LANGUAGES:
        lang = "uk"
    
    # Get the current year for the copyright notice
    current_year = datetime.now().year
    
    # Load translations
    try:
        with open('static/translations.json', 'r', encoding='utf-8') as f:
            translations = json.load(f)
    except Exception as e:
        print(f"Error loading translations: {e}")
        translations = {}
    
    return templates.TemplateResponse(
        "assistant.html",
        {
            "request": request,
            "lang": lang,
            "lang_name": SUPPORTED_LANGUAGES[lang],
            "supported_languages": SUPPORTED_LANGUAGES,
            "welcome_message": WELCOME_MESSAGES[lang],
            "destinations": DESTINATIONS.get(lang, DESTINATIONS["en"]),
            "current_year": current_year,
            "translations": translations
        }
    )

@app.post("/api/chat")
async def chat(chat_request: ChatRequest):
    """API endpoint for chat interactions"""
    # Generate a session ID if none provided
    session_id = chat_request.session_id or str(uuid.uuid4())
    
    # Extract travel info from message
    travel_info = extract_travel_info(chat_request.message)
    
    # Extract contact info from message
    contact_info = extract_email(chat_request.message) or extract_phone(chat_request.message)
    if contact_info:
        # Create a contact record
        contact_data = {
            "name": chat_request.user_info.get("name", "Not provided") if chat_request.user_info else "Not provided",
            "contact": contact_info,
            "destination": travel_info.get("destination", "Not specified"),
            "interests": chat_request.user_info.get("interests", []) if chat_request.user_info else [],
            "budget": chat_request.user_info.get("budget") if chat_request.user_info else None,
            "language": chat_request.lang
        }
        
        # Save contact to sheet
        save_contact_to_sheet(contact_data)
    
    # Get AI response
    response = get_ai_response(
        message=chat_request.message,
        lang=chat_request.lang,
        session_id=session_id,
        user_info=chat_request.user_info
    )
    
    return {
        "response": response,
        "session_id": session_id,
        "contact_saved": bool(contact_info),
        "detected_info": travel_info
    }

@app.post("/api/language")
async def change_language(language_request: LanguageRequest):
    """API endpoint for changing language"""
    lang = language_request.lang
    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"
    
    return {
        "success": True,
        "lang": lang,
        "welcome_message": WELCOME_MESSAGES[lang]
    }

# Helper functions
def extract_email(message):
    """Extract email address from message"""
    email_pattern = r'[^\s@]+@[^\s@]+\.[^\s@]+'
    email_match = re.search(email_pattern, message)
    if email_match:
        email = email_match.group(0).strip(',.!?;:()')
        print(f"Found email: {email}")
        return email
    return None

def extract_phone(message):
    """Extract phone number from message"""
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

def extract_travel_info(message):
    """Extract travel information from message"""
    info = {
        "destination": None
    }
    
    # Extract destination
    countries = extract_countries(message)
    if countries:
        info["destination"] = countries[0].capitalize()
        print(f"Set destination to: {countries[0].capitalize()}")
    
    return info

def extract_countries(message):
    """Extract country names from message"""
    message_lower = message.lower()
    
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
        "bali", "bali", "балі", "бали", "bali",
        "kyiv", "kiew", "київ", "киев", "kiev",
        "barcelona", "barcelona", "барселона", "барселона", "barcelona",
        "tokyo", "tokio", "токіо", "токио", "tokyo",
        "santorini", "santorini", "санторіні", "санторини", "santorini",
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

def save_contact_to_sheet(contact_data):
    """Save contact information to Google Sheets"""
    try:
        # Ensure we have a contact to save
        if not contact_data.get("contact"):
            print("No contact to save")
            return False
        
        print(f"Data to save: {contact_data}")
        
        # Try to use Google Sheets
        creds_file = "google_credentials.json"
        google_creds = os.getenv("GOOGLE_CREDENTIALS")
        
        # Create credentials file from environment if it doesn't exist
        if not os.path.exists(creds_file) and google_creds:
            with open(creds_file, "w") as f:
                f.write(google_creds)
        
        # Set up Google Sheets credentials
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(credentials)
        
        # Get spreadsheet ID from URL
        sheet_url = "https://docs.google.com/spreadsheets/d/1u0oWbOWXJaPwKfBXBrebc67s0PAz1tgCh7Og_Neaofk/edit?gid=0#gid=0"
        sheet_id = sheet_url.split("/d/")[1].split("/")[0]
        
        # Open sheet and add row
        sheet = client.open_by_key(sheet_id).sheet1
        
        # Add the row with all data
        row_data = [
            contact_data.get("name", "Not provided"),
            contact_data.get("contact"),
            contact_data.get("destination", "Not specified"),
            ", ".join(contact_data.get("interests", [])) if isinstance(contact_data.get("interests"), list) else "Not specified",
            contact_data.get("budget") or "Not specified",
            contact_data.get("language") or "en",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        
        print(f"Row data: {row_data}")
        sheet.append_row(row_data)
        print(f"Successfully saved contact data to Google Sheet")
        
        return True
        
    except Exception as e:
        print(f"Error saving to Google Sheet: {e}")
        # More detailed error trace
        import traceback
        print(traceback.format_exc())
        
        # Try CSV fallback
        try:
            fallback_file = "contact_leads.csv"
            import csv
            file_exists = os.path.exists(fallback_file)
            with open(fallback_file, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Name", "Contact", "Destination", "Interests", "Budget", "Language", "Timestamp"])
                writer.writerow([
                    contact_data.get("name", "Not provided"),
                    contact_data.get("contact"),
                    contact_data.get("destination", "Not specified"),
                    ", ".join(contact_data.get("interests", [])) if isinstance(contact_data.get("interests"), list) else "Not specified",
                    contact_data.get("budget") or "Not specified",
                    contact_data.get("language") or "en",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ])
            print(f"Saved to local CSV file: {fallback_file}")
            return True
        except Exception as csv_err:
            print(f"Error saving to CSV: {str(csv_err)}")
            return False

def get_conversation_history(session_id):
    """Get conversation history for a session or create new one"""
    history_dir = "conversations"
    os.makedirs(history_dir, exist_ok=True)
    
    history_file = f"{history_dir}/{session_id}.json"
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            # If file is corrupted, start fresh
            return []
    else:
        return []

def save_conversation_history(session_id, history):
    """Save conversation history for a session"""
    history_dir = "conversations"
    os.makedirs(history_dir, exist_ok=True)
    
    history_file = f"{history_dir}/{session_id}.json"
    
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_system_message(lang='en'):
    """Create system message based on language"""
    base_messages = {
        "en": """You are a friendly and knowledgeable travel agent for Alligator.tour travel agency. 
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
        """,
        "de": """Du bist ein freundlicher und kenntnisreicher Reiseberater für die Alligator.tour Reiseagentur.
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
        """,
        "uk": """Ви дружелюбний та компетентний туристичний агент агентства Alligator.tour.
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
        """,
        # Include other languages here
    }
    
    # Use English as default if language not supported
    return base_messages.get(lang, base_messages["en"])

def get_ai_response(message, lang='en', session_id='default', user_info=None):
    """Get response from OpenAI API"""
    try:
        # Load conversation history from session or initialize new one
        conversation_history = get_conversation_history(session_id)
        
        # Create system message based on language
        system_message = get_system_message(lang)
        
        # Prepare messages for API call
        messages = [{"role": "system", "content": system_message}]
        
        # Add conversation history
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add user message
        messages.append({"role": "user", "content": message})
        
        # Add user info context if available
        if user_info:
            context = f"\nCurrent user information: {json.dumps(user_info)}"
            messages[-1]["content"] += context
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=800
        )
        
        response_content = response.choices[0].message["content"]
        
        # Save conversation
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": response_content})
        save_conversation_history(session_id, conversation_history)
        
        return response_content
    except Exception as e:
        # Provide error message in appropriate language
        error_messages = {
            "en": f"I'm having trouble connecting. Please try again later. Error: {str(e)}",
            "de": f"Ich habe Verbindungsprobleme. Bitte versuchen Sie es später noch einmal. Fehler: {str(e)}",
            "uk": f"У мене виникли проблеми з підключенням. Будь ласка, спробуйте пізніше. Помилка: {str(e)}",
            "ru": f"У меня возникли проблемы с подключением. Пожалуйста, повторите попытку позже. Ошибка: {str(e)}",
            "ro": f"Am probleme cu conectarea. Vă rugăm să încercați din nou mai târziu. Eroare: {str(e)}"
        }
        return error_messages.get(lang, error_messages["en"])

# Ensure required directories exist
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("static/images", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("conversations", exist_ok=True)

# Main entry point
if __name__ == "__main__":
    # Set port from environment variable or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    # Set host from environment variable or default to 0.0.0.0
    host = os.getenv("HOST", "0.0.0.0")
    
    # Run the FastAPI app using uvicorn
    uvicorn.run("app:app", host=host, port=port, reload=True)