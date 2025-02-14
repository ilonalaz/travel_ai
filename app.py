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

# Load environment variables
load_dotenv()

# Set OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Load credentials from Streamlit Secrets
creds_dict = st.secrets["google_sheets"]

# Authenticate with Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open Google Sheet by ID
SPREADSHEET_ID = "1u0oWbOWXJaPwKfBXBrebc67s0PAz1tgCh7Og_Neaofk"  # Your actual sheet ID
sheet = client.open_by_key(SPREADSHEET_ID).sheet1
try:
    SPREADSHEET_ID = "1u0oWbOWXJaPwKfBXBrebc67s0PAz1tgCh7Og_Neaofk"
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    print("✅ Successfully connected to Google Sheets!")  # Debugging message
except Exception as e:
    st.error(f"❌ Google Sheets Permission Error: {e}")  # Show full error message

def save_request(name, contact, destination, start_date, end_date, num_people):
    """Saves travel request to Google Sheets instead of CSV."""
    try:
        sheet.append_row([name, contact, destination, start_date, end_date, num_people])
        st.success("✅ Your travel request has been saved to Google Sheets!")
    except Exception as e:
        st.error(f"⚠️ Error saving to Google Sheets: {e}")

# Initialize session state
if "show_consultation" not in st.session_state:
    st.session_state.show_consultation = False

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

# Function to generate activity descriptions using OpenAI
def get_activity_descriptions(destination):
    """Fetches recommended activities from OpenAI and finds related images."""
    prompt = f"""
    Provide a list of 3 recommended activities for a traveler visiting {destination}.
    Each activity should have a clear title followed by a short engaging description.
    
    Format it exactly like this:
    
    Activity Title: Description of the activity, what makes it special, and what travelers can experience there.
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a travel expert providing recommendations."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
        )
        
        activities = response.choices[0].message.content.strip().split("\n")
        formatted_activities = []

        for activity in activities:
            if ":" in activity:
                title, description = activity.split(":", 1)
                # Fetch image from Unsplash (or use Google Image Search)
                image_url = f"https://source.unsplash.com/400x300/?{title.strip().replace(' ', '%20')}"
                formatted_activities.append((title.strip(), description.strip(), image_url))

        return formatted_activities
    except Exception as e:
        return [("⚠️ Error", str(e), "")]

# Function to save requests
def save_request(name, contact, destination, start_date, end_date, num_people):
    file_path = "travel_requests.csv"
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Name", "Contact", "Destination", "Start Date", "End Date", "People"])
        writer.writerow([name, contact, destination, start_date, end_date, num_people])

    st.success("✅ Your travel request has been saved! Our agent will contact you soon.")

# Streamlit App UI
st.title("🌍 Travel Planner Chatbot ✈️")
st.write("Plan your trip, find flights, hotels, and activities effortlessly!")

# User Inputs
destination = st.text_input("🌍 Where do you want to travel?", st.session_state.get("destination", ""))
start_date = st.date_input("📅 Start Date", st.session_state.get("start_date", None))
end_date = st.date_input("📅 End Date", st.session_state.get("end_date", None))
num_people = st.number_input("👥 Number of people", min_value=1, step=1, value=st.session_state.get("num_people", 1))

if st.button("🔍 Search for Flights & Hotels"):
    if destination and start_date and end_date:
        # Store inputs in session state
        st.session_state.destination = destination
        st.session_state.start_date = start_date
        st.session_state.end_date = end_date
        st.session_state.num_people = num_people

        st.subheader("✈️ Available Flights:")
        flights = search_flights(destination, start_date, end_date)
        for flight in flights:
            st.markdown(f"- {flight}")

        st.subheader("🏨 Available Hotels:")
        hotels = search_hotels(destination)
        for hotel in hotels:
            st.markdown(f"- {hotel}")

        st.subheader("🎡 Recommended Activities:")
        activities = get_activity_descriptions(destination)
        
        for title, description, image_url in activities:
            st.markdown(f"**{title}**")
            st.write(description)
            st.image(image_url, caption=title, use_column_width=True)

        # Show consultation button
        st.session_state.show_consultation = True
    else:
        st.warning("⚠️ Please enter all required details before searching.")

# Show consultation form only if the button was clicked
if st.session_state.show_consultation:
    st.subheader("💬 Private Consultation")
    name = st.text_input("Your Name", st.session_state.get("name", ""))
    contact = st.text_input("Your Contact (Email/Phone)", st.session_state.get("contact", ""))

    if st.button("Submit Request"):
        if name and contact:
            save_request(name, contact, destination, start_date, end_date, num_people)
            st.session_state.show_consultation = False  # Hide the form after submitting
        else:
            st.warning("⚠️ Please enter your name and contact details.")
