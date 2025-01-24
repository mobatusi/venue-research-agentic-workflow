import os
import sys
import requests  # Import requests for API testing

import streamlit as st

# Handle SQLite for Streamlit Cloud compatibility
try:
    import sqlite3
    sqlite3.connect(':memory:')
except sqlite3.OperationalError:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from pathlib import Path
import datetime
import asyncio
from datetime import datetime, timedelta

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from venue_score_flow.main import run_with_inputs, run
from venue_score_flow.constants import EMAIL_TEMPLATE

def test_openai_api_key(api_key):
    """Test the OpenAI API key by making a simple request."""
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.get("https://api.openai.com/v1/models", headers=headers)
        return response.status_code == 200  # Return True if the request was successful
    except Exception as e:
        st.error(f"Error testing OpenAI API key: {e}")
        return False

def test_serper_api_key(api_key):
    """Test the Serper API key by making a simple request."""
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.get("https://google.serper.dev/scholar", headers=headers)
        return response.status_code == 200  # Return True if the request was successful
    except Exception as e:
        st.error(f"Error testing Serper API key: {e}")
        return False

def test_serper_api_key(api_key):
    os.environ['SERPER_API_KEY'] = api_key
    from crewai_tools import SerperDevTool

    tool = SerperDevTool(
        search_url="https://google.serper.dev/scholar",
        n_results=2,
    )
    try:
        if tool.run(search_query="ChatGPT"):
            return True
    except Exception as e:
        st.error(f"Error testing Serper API key: {e}")
        return False

def main():
    st.set_page_config(
        page_title="Venue Search Workflow",
        page_icon="🏢",
        layout="wide"
    )
    st.title("🏢 Venue Search Workflow")
    st.write("Enter an address and search radius to find and analyze venues in the area.")

    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")
        with st.expander("ℹ️ About this tool", expanded=True):
            st.write("""
            This tool helps you:
            1. 🔍 Search for venues around a specific location
            2. 📊 Score the venues found
            3. 📧 Create outreach emails
            
            Make sure you have set up your API keys before starting.
            """)

        # API Keys Configuration
        st.subheader("API Configuration")
        
        # OpenAI API Key input
        openai_key = st.text_input(
            "OpenAI API Key",
            value="",
            type="password",
            placeholder="Enter your OpenAI API key",
            help="Acquire an OpenAI API key by registering for a free account at openai.com",
            key="openai_key_input"
        )

        # Serper API Key input
        serper_key = st.text_input(
            "Serper API Key",
            value="",
            type="password",
            placeholder="Enter your Serper API key",
            help="Acquire a serper.dev API key by registering for a free account at serper.dev",
            key="serper_key_input"
        )

        # Initialize validity flags in session state if not already set
        if 'openai_key_valid' not in st.session_state:
            st.session_state['openai_key_valid'] = False
        if 'serper_key_valid' not in st.session_state:
            st.session_state['serper_key_valid'] = False

        # Validate API keys
        if st.button("Validate API Keys"):
            if openai_key and serper_key:
                st.session_state['openai_key_valid'] = test_openai_api_key(openai_key)
                if st.session_state['openai_key_valid']:
                    st.success("✅ OpenAI API key is valid.")
                    os.environ['OPENAI_API_KEY'] = openai_key  # Set environment variable
                else:
                    st.error("❌ OpenAI API key is invalid.")

                st.session_state['serper_key_valid'] = test_serper_api_key(serper_key)
                if st.session_state['serper_key_valid']:
                    st.success("✅ Serper API key is valid.")
                    os.environ['SERPER_API_KEY'] = serper_key  # Set environment variable
                else:
                    st.error("❌ Serper API key is invalid.")
            else:
                st.error("⚠️ Please enter both API keys.")

    # Initialize sender_name, sender_email, and email_template
    sender_name = st.session_state.get("sender_name", "John Doe")  # Default value
    sender_email = st.session_state.get("sender_email", "john.doe@example.com")  # Default value
    email_template = st.session_state.get("email_template", EMAIL_TEMPLATE)  # Default email template

    # Collect user inputs
    address = st.text_input("Search Location", "333 Adams St, Brooklyn, NY 11201, United States", key="address_input")
    radius_km = st.slider("Search Radius", 0.1, 2.0, 0.5, key="radius_input")
    event_date = st.date_input("Event Date", datetime.now() + timedelta(days=90), key="event_date_input")
    event_time = st.text_input("Event Time", "2:00 PM", key="event_time_input")
    sender_name = st.text_input("Sender Name", "John Doe", key="sender_name_input")
    sender_email = st.text_input("Sender Email", "john.doe@example.com", key="sender_email_input")

    # Use a checkbox to toggle the email template form
    use_custom_template = st.checkbox("Use Custom Email Template", key="use_custom_template")
    formatted_template = ""
    if use_custom_template:
        # Show social media input fields
        st.subheader("Social Media Links")
        linkedin_url = st.text_input("LinkedIn URL", "https://linkedin.com/company/mycompany", key="linkedin_url_input")
        instagram_url = st.text_input("Instagram URL", "https://instagram.com/mycompany", key="instagram_url_input")
        tiktok_url = st.text_input("TikTok URL", "https://tiktok.com/@mycompany", key="tiktok_url_input")

        # Replace placeholders in the email template dynamically
        formatted_template = email_template
        formatted_template = formatted_template.replace("{event_date}", event_date.strftime('%A %B %d, %Y'))
        formatted_template = formatted_template.replace("{event_time}", event_time)
        formatted_template = formatted_template.replace("{sender_name}", sender_name)
        formatted_template = formatted_template.replace("{sender_email}", sender_email)
        formatted_template = formatted_template.replace("{linkedin_url}", linkedin_url)
        formatted_template = formatted_template.replace("{instagram_url}", instagram_url)
        formatted_template = formatted_template.replace("{tiktok_url}", tiktok_url)

        st.text_area("Email Template Preview", formatted_template, height=300)

    # Search button
    # Enable search button only if both API keys are valid
    search_button_disabled = not (st.session_state['openai_key_valid'] and st.session_state['serper_key_valid'])
    if search_button_disabled:
        st.warning("⚠️ Please configure both OpenAI and Serper API keys before searching")
    else:
        if st.button("🔍 Start Search"):
            # Run the workflow and display results
            with st.spinner("Searching for venues..."):
                inputs = {
                    "address": address,
                    "radius_km": radius_km,
                    "event_date": event_date.strftime('%Y-%m-%d'),
                    "event_time": event_time,
                    "sender_name": sender_name,
                    "sender_email": sender_email,
                    "email_template": formatted_template,
                    "openai_key": openai_key,
                    "serper_key": serper_key,
                }

                # Run the workflow and display results
                result = asyncio.run(run_with_inputs(inputs))
                if result:
                    st.json(result.model_dump_json(indent=2))
                    # Write results to JSON file after user confirms
                    with open('venue_search_results.json', 'w', encoding='utf-8') as f:
                        f.write(result.model_dump_json(indent=2))
                    st.success("Results written to venue_search_results.json")

                    if formatted_template != "":
                        # Create the directory 'email_responses' if it doesn't exist
                        output_dir = Path(__file__).parent / "email_responses"
                        print("output_dir:", output_dir)
                        output_dir.mkdir(parents=True, exist_ok=True)

                        # Use the venue names from the update the email template with the venue names
                        for venue in result.hydrated_venues:
                            formatted_template = formatted_template.replace("{venue_name}", venue.name)
                            # Write emails to file
                            email_path = output_dir / f'emails_{venue.name}.txt'
                            with open(email_path, 'w', encoding='utf-8') as f:
                                f.write(formatted_template)
                        st.success("Emails written to email_responses directory")
                else:
                    st.error("Failed to retrieve results. Please check the agent configuration.")

if __name__ == "__main__":
    main()
