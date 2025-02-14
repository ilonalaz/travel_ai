import os
import csv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import streamlit as st
from duckduckgo_search import DDGS
from dotenv import load_dotenv
import openai  
import requests
import googleapiclient.discovery

# Load API keys
openai_api_key = st.secrets["OPENAI_API_KEY"]

creds_dict = dict(st.secrets["google_sheets"])  

# Authenticate with Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open Google Sheet by ID
SPREADSHEET_ID = "1u0oWbOWXJaPwKfBXBrebc67s0PAz1tgCh7Og_Neaofk"
sheet = client.open_by_key(SPREADSHEET_ID).sheet1  

# Initialize session state
if "show_consultation" not in st.session_state:
    st.session_state.show_consultation = False

# Default language session state
if "language" not in st.session_state:
    st.session_state.language = "en"

# Define language options at the very top
LANGUAGES = {
    "English": "en",
    "Deutsch (German)": "de",
    "Українська (Ukrainian)": "uk",
    "Русский (Russian)": "ru",
    "Română (Romanian)": "ro"
}

# Initialize session state for language selection
if "language" not in st.session_state:
    st.session_state.language = "en"

# Language selection dropdown
selected_language = st.selectbox("🌍 Choose your language:", list(LANGUAGES.keys()))
st.session_state.language = LANGUAGES[selected_language]  # Store selected language

# Translation Dictionary
TRANSLATIONS = {
    "en": {
        "title": "🌍 Travel Planner Chatbot ✈️",
        "description": "Plan your trip, find flights, hotels, and activities effortlessly!",
        "destination": "🌍 Where do you want to travel?",
        "start_date": "📅 Start Date",
        "end_date": "📅 End Date",
        "num_people": "👥 Number of people",
        "search_button": "🔍 Search for Flights & Hotels",
        "flights": "✈️ Available Flights:",
        "hotels": "🏨 Available Hotels:",
        "activities": "🎡 Recommended Activities:",
        "consultation": "💬 Private Consultation",
        "name": "Your Name",
        "contact": "Your Contact (Email/Phone)",
        "submit": "Submit Request",
        "success_save": "✅ Your travel request has been saved to Google Sheets!",
        "error_save": "⚠️ Error saving to Google Sheets: {}",
    },
    "de": {
        "title": "🌍 Reiseplaner Chatbot ✈️",
        "description": "Planen Sie Ihre Reise, finden Sie Flüge, Hotels und Aktivitäten mühelos!",
        "destination": "🌍 Wohin möchten Sie reisen?",
        "start_date": "📅 Startdatum",
        "end_date": "📅 Enddatum",
        "num_people": "👥 Anzahl der Personen",
        "search_button": "🔍 Flüge & Hotels suchen",
        "flights": "✈️ Verfügbare Flüge:",
        "hotels": "🏨 Verfügbare Hotels:",
        "activities": "🎡 Empfohlene Aktivitäten:",
        "consultation": "💬 Private Beratung",
        "name": "Ihr Name",
        "contact": "Ihr Kontakt (E-Mail/Telefon)",
        "submit": "Anfrage absenden",
        "success_save": "✅ Ihre Reiseanfrage wurde in Google Sheets gespeichert!",
        "error_save": "⚠️ Fehler beim Speichern in Google Sheets: {}",
    },
    "uk": {
        "title": "🌍 Планувальник подорожей ✈️",
        "description": "Плануйте свою подорож, знаходьте рейси, готелі та активності легко!",
        "destination": "🌍 Куди ви хочете подорожувати?",
        "start_date": "📅 Дата початку",
        "end_date": "📅 Дата закінчення",
        "num_people": "👥 Кількість людей",
        "search_button": "🔍 Шукати авіаквитки та готелі",
        "flights": "✈️ Доступні рейси:",
        "hotels": "🏨 Доступні готелі:",
        "activities": "🎡 Рекомендовані активності:",
        "consultation": "💬 Приватна консультація",
        "name": "Ваше ім'я",
        "contact": "Ваш контакт (E-mail/телефон)",
        "submit": "Надіслати запит",
        "success_save": "✅ Ваш запит на подорож збережено в Google Sheets!",
        "error_save": "⚠️ Помилка збереження в Google Sheets: {}",
    },
    "ru": {
        "title": "🌍 Планировщик путешествий ✈️",
        "description": "Планируйте поездку, находите билеты, отели и мероприятия легко!",
        "destination": "🌍 Куда вы хотите поехать?",
        "start_date": "📅 Дата начала",
        "end_date": "📅 Дата окончания",
        "num_people": "👥 Количество людей",
        "search_button": "🔍 Искать билеты и отели",
        "flights": "✈️ Доступные рейсы:",
        "hotels": "🏨 Доступные отели:",
        "activities": "🎡 Рекомендуемые развлечения:",
        "consultation": "💬 Частная консультация",
        "name": "Ваше имя",
        "contact": "Ваш контакт (Email/Телефон)",
        "submit": "Отправить запрос",
        "success_save": "✅ Ваш запрос на путешествие сохранен в Google Sheets!",
        "error_save": "⚠️ Ошибка сохранения в Google Sheets: {}",
    },
    "ro": {
        "title": "🌍 Planificator de călătorii ✈️",
        "description": "Planificați călătoria, găsiți zboruri, hoteluri și activități fără efort!",
        "destination": "🌍 Unde doriți să călătoriți?",
        "start_date": "📅 Data de început",
        "end_date": "📅 Data de sfârșit",
        "num_people": "👥 Număr de persoane",
        "search_button": "🔍 Căutare zboruri și hoteluri",
        "flights": "✈️ Zboruri disponibile:",
        "hotels": "🏨 Hoteluri disponibile:",
        "activities": "🎡 Activități recomandate:",
        "consultation": "💬 Consultație privată",
        "name": "Numele dvs.",
        "contact": "Contactul dvs. (E-mail/Telefon)",
        "submit": "Trimite cererea",
        "success_save": "✅ Cererea dvs. de călătorie a fost salvată în Google Sheets!",
        "error_save": "⚠️ Eroare la salvarea în Google Sheets: {}",
    }
}

# Function to search flights
def search_flights(destination, start_date, end_date):
    query = f"Best flights to {destination} from {start_date} to {end_date}"
    results = DDGS().text(query, max_results=3)
    
    flights = [f"✈️ [{result['title']}]({result['href']})" for result in results]
    return flights if flights else ["⚠️ No flights found."]

# Function to search hotels
def search_hotels(destination):
    query = f"Cheapest hotels in {destination} for 2 people"
    results = DDGS().text(query, max_results=3)
    
    hotels = [f"🏨 [{result['title']}]({result['href']})" for result in results]
    return hotels if hotels else ["⚠️ No hotels found."]

# Function to generate activity descriptions using OpenAI (Now supports multiple languages)
def get_activity_descriptions(destination):
    """Fetches recommended activities from OpenAI in the selected language."""
    
    lang = st.session_state.language  # Get selected language from session state

    # Define mapping from language codes to OpenAI-supported language names
    language_names = {
        "en": "English",
        "de": "German",
        "uk": "Ukrainian",
        "ru": "Russian",
        "ro": "Romanian"
    }

    # Ensure we have a valid language, default to English
    prompt_language = language_names.get(lang, "English")  

    prompt = f"""
    Provide a list of 3 recommended activities for a traveler visiting {destination}.
    Each activity should have a clear title (without the words 'Activity Title') followed by a detailed yet concise description.

    Format it exactly like this:

    Activity Title: A compelling and informative description of the activity, explaining what makes it special, what visitors can experience, and why it is recommended.

    Do not include the words 'Activity Title' in your response.

    Respond in {prompt_language}.
    """

    try:
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a travel expert providing recommendations."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,  # Increased from 600 to prevent truncation
        )

        activities_text = response.choices[0].message.content.strip()

        activities_list = activities_text.split("\n")
        formatted_activities = []

        for activity in activities_list:
            if ":" in activity:
                title, description = activity.split(":", 1)
                title = title.strip().replace("Activity Title", "").replace("Title", "").strip()  # Remove unwanted words
                formatted_activities.append((title, description.strip()))

        return formatted_activities if formatted_activities else [("⚠️ No activities found", "Try again later.")]
    except Exception as e:
        st.error(f"⚠️ OpenAI Error: {e}")
        return [("⚠️ Error", str(e))]


# Function to save requests
def save_request(name, contact, destination, start_date, end_date, num_people):
    """Saves travel request to Google Sheets"""
    try:
        sheet.append_row([name, contact, destination, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), num_people])
        st.success(TRANSLATIONS[st.session_state.language]["success_save"])
    except Exception as e:
        st.error(TRANSLATIONS[st.session_state.language]["error_save"].format(e))

# Streamlit App UI
lang = st.session_state.language
st.title(TRANSLATIONS[lang]["title"])
st.write(TRANSLATIONS[lang]["description"])

destination = st.text_input(TRANSLATIONS[lang]["destination"])
start_date = st.date_input(TRANSLATIONS[lang]["start_date"])
end_date = st.date_input(TRANSLATIONS[lang]["end_date"])
num_people = st.number_input("👥 Number of people", min_value=1, step=1)

if st.button(TRANSLATIONS[lang]["search_button"]):
    if destination and start_date and end_date:
        # Store inputs in session state
        st.session_state.destination = destination
        st.session_state.start_date = start_date
        st.session_state.end_date = end_date
        st.session_state.num_people = num_people

        # Fetch results and store in session state
        st.session_state.flights = search_flights(destination, start_date, end_date)
        st.session_state.hotels = search_hotels(destination)

        activities = get_activity_descriptions(destination)  # ✅ Fetch activities

        if activities:  # ✅ Ensure activities exist before storing
            st.session_state.activities = activities
        else:
            st.session_state.activities = [("⚠️ No activities found", "Try again later.")]
        
        st.session_state.show_consultation = True  # ✅ Ensure consultation appears
        
# Display results only if they exist in session state
if "flights" in st.session_state:
    st.subheader(TRANSLATIONS[lang]["flights"])
    for flight in st.session_state.flights:
        st.markdown(f"- {flight}")

if "hotels" in st.session_state:
    st.subheader(TRANSLATIONS[lang]["hotels"])
    for hotel in st.session_state.hotels:
        st.markdown(f"- {hotel}")
        
# Display activities only if they exist
if "activities" in st.session_state and st.session_state.activities:
    st.subheader(TRANSLATIONS[lang]["activities"])
    
    for activity in st.session_state.activities:
        if len(activity) == 2:  # Ensure there are both a title and description
            title, description = activity
            st.markdown(f"### {title}")  # ✅ Use markdown to make title prominent
            st.write(description)
        else:
            st.warning("⚠️ Activity data is incorrectly formatted.")
else:
    st.warning("⚠️ No activities found. Try again!")


if "show_consultation" not in st.session_state:
    st.session_state.show_consultation = False

if st.session_state.show_consultation:
    st.subheader(TRANSLATIONS[lang]["consultation"])
    name = st.text_input(TRANSLATIONS[lang]["name"])
    contact = st.text_input(TRANSLATIONS[lang]["contact"])

    if st.button(TRANSLATIONS[lang]["submit"]):
        if name and contact:
            save_request(name, contact, destination, start_date, end_date, num_people)
            st.success("✅ Request submitted successfully!")
            st.session_state.show_consultation = False  # Hide form after submitting
        else:
            st.warning("⚠️ Please enter your name and contact details.")
