import os
import csv
from duckduckgo_search import DDGS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Access API keys from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")

def get_user_input():
    print("\nWelcome to the Travel Planner Chatbot! ✈️\n")
    destination = input("Where do you want to travel? ")
    start_date = input("Start date (YYYY-MM-DD): ")
    end_date = input("End date (YYYY-MM-DD): ")
    num_people = input("How many people? ")
    
    return destination, start_date, end_date, num_people

def search_flights(destination, start_date, end_date):
    """Search the web for flight options."""
    query = f"Best flights to {destination} from {start_date} to {end_date}"
    results = DDGS().text(query, max_results=3)
    
    flights = []
    for result in results:
        flights.append(f"✈️ {result['title']} - {result['href']}")
    
    return flights if flights else ["⚠️ No flights found."]

def search_hotels(destination):
    """Search the web for hotel options."""
    query = f"Cheapest hotels in {destination} for 2 people"
    results = DDGS().text(query, max_results=3)
    
    hotels = []
    for result in results:
        hotels.append(f"🏨 {result['title']} - {result['href']}")
    
    return hotels if hotels else ["⚠️ No hotels found."]

def save_request(name, contact, destination, start_date, end_date, num_people):
    """Saves travel requests to a CSV file."""
    file_path = "travel_requests.csv"
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Name", "Contact", "Destination", "Start Date", "End Date", "People"])
        writer.writerow([name, contact, destination, start_date, end_date, num_people])

    print("\n✅ Your travel request has been saved! Our agent will contact you soon.\n")

def plan_trip(destination, start_date, end_date, num_people):
    """Fetches flights, hotels, and activities."""
    print("\n🔎 Searching flights and hotels... 🛫🏨\n")
    
    flights = search_flights(destination, start_date, end_date)
    hotels = search_hotels(destination)

    activities = [
        "Senso-ji Temple",
        "Shibuya Crossing",
        "Tokyo Skytree"
    ]  # Keep 3 activities

    return {
        "Flights": flights,
        "Hotels": hotels,
        "Activities": activities
    }

def main():
    """Main chatbot function."""
    destination, start_date, end_date, num_people = get_user_input()
    print("\n📍 Planning your trip... This may take a moment... 🛫\n")
    trip_plan = plan_trip(destination, start_date, end_date, num_people)

    print("\n📋 **Here’s your personalized travel plan:**\n")

    # Display Flights
    print("\n✈️ **Available Flights:**")
    for flight in trip_plan["Flights"]:
        print(f"   - {flight}")

    # Display Hotels
    print("\n🏨 **Available Hotels:**")
    for hotel in trip_plan["Hotels"]:
        print(f"   - {hotel}")

    # Display Activities
    print("\n🎡 **Recommended Activities:**")
    for activity in trip_plan["Activities"]:
        print(f"   - {activity}")

    # Ask for Private Consultation
    consultation = input("\nWould you like to have a private consultation with our travel agency? (yes/no): ")
    if consultation.lower() == "yes":
        name = input("Please enter your name: ")
        contact = input("Please enter your contact details (email/phone): ")
        save_request(name, contact, destination, start_date, end_date, num_people)
    else:
        print("\nThank you for using our travel planner! Have a great trip! ✈️")

if __name__ == "__main__":
    main()
