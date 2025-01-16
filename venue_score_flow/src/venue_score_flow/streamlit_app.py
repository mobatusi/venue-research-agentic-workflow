import streamlit as st
import asyncio
from venue_score_flow.main import run_with_inputs
from venue_score_flow.constants import EMAIL_TEMPLATE
import os
from datetime import datetime, timedelta
import datetime as dt

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
        openai_key_input = st.text_input(
            "OpenAI API Key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            placeholder="Enter your OpenAI API key",
            help="Required for AI-powered analysis and content generation",
            key="openai_key_input"
        )
        
        # Serper API Key input
        serper_key_input = st.text_input(
            "Serper API Key",
            value=os.getenv("SERPER_API_KEY", ""),
            type="password",
            placeholder="Enter your Serper API key",
            help="Required for web search functionality",
            key="serper_key_input"
        )
        
        # Show API configuration status
        if openai_key_input or serper_key_input:
            st.write("**API Configuration Status:**")
            if openai_key_input:
                st.success("✅ OpenAI API key set")
            else:
                st.error("❌ OpenAI API key missing")
                
            if serper_key_input:
                st.success("✅ Serper API key set")
            else:
                st.error("❌ Serper API key missing")

    # Initialize sender_name, sender_email, and email_template
    sender_name = st.session_state.get("sender_name", "John Doe")  # Default value
    sender_email = st.session_state.get("sender_email", "john.doe@example.com")  # Default value
    email_template = st.session_state.get("email_template", EMAIL_TEMPLATE)  # Default email template

    # Collect user inputs
    address = st.text_input("Search Location", "333 Adams St, Brooklyn, NY 11201, United States", key="address_input")
    radius_km = st.slider("Search Radius", 0.1, 2.0, 0.5, key="radius_input")
    event_date = st.date_input("Event Date", datetime.now() + timedelta(days=90), key="event_date_input")
    event_time = st.time_input("Event Time", dt.time(14, 0), key="event_time_input")
    sender_name = st.text_input("Sender Name", "John Doe", key="sender_name_input")
    sender_email = st.text_input("Sender Email", "john.doe@example.com", key="sender_email_input")

    # Use a checkbox to toggle the email template form
    use_custom_template = st.checkbox("Use Custom Email Template", key="use_custom_template")

    if use_custom_template:
        # Show social media input fields
        st.subheader("Social Media Links")
        linkedin_url = st.text_input("LinkedIn URL", "https://linkedin.com/company/mycompany", key="linkedin_url_input")
        instagram_url = st.text_input("Instagram URL", "https://instagram.com/mycompany", key="instagram_url_input")
        tiktok_url = st.text_input("TikTok URL", "https://tiktok.com/@mycompany", key="tiktok_url_input")

        # Replace placeholders in the email template dynamically
        formatted_template = email_template
        formatted_template = formatted_template.replace("{event_date}", event_date.strftime('%A %B %d, %Y'))
        formatted_template = formatted_template.replace("{event_time}", event_time.strftime('%I:%M %p'))
        formatted_template = formatted_template.replace("{sender_name}", sender_name)
        formatted_template = formatted_template.replace("{sender_email}", sender_email)
        formatted_template = formatted_template.replace("{linkedin_url}", linkedin_url)
        formatted_template = formatted_template.replace("{instagram_url}", instagram_url)
        formatted_template = formatted_template.replace("{tiktok_url}", tiktok_url)


        st.text_area("Email Template Preview", formatted_template, height=300)

    # Search button
    if st.button("🔍 Start Search"):
        inputs = {
            "address": address,
            "radius_km": radius_km,
            "event_date": event_date.strftime('%Y-%m-%d'),
            "event_time": event_time.strftime('%I:%M %p'),
            "sender_name": sender_name,
            "sender_email": sender_email,
            "email_template": formatted_template
        }

        # Run the workflow and display results
        result = asyncio.run(run_with_inputs(inputs))
        if result:
            st.json(result.model_dump_json(indent=2))

            # Present options to the user based on the results
            options = ["Quit", "Redo lead scoring with additional feedback", "Proceed with writing emails to all venues"]
            choice = st.selectbox("Please choose an option:", options)

            if choice == "Quit":
                st.write("Exiting the program.")
            elif choice == "Redo lead scoring with additional feedback":
                feedback = st.text_input("Please provide additional feedback:")
                if st.button("Submit Feedback"):
                    # Handle feedback submission
                    st.success("Feedback submitted.")
            elif choice == "Proceed with writing emails to all venues":
                st.write("Proceeding to write emails to all venues.")
                
                # Write results to JSON file after user confirms
                with open('venue_search_results.json', 'w', encoding='utf-8') as f:
                    f.write(result.model_dump_json(indent=2))
                st.success("Results written to venue_search_results.json")
        else:
            st.error("Failed to retrieve results. Please check the agent configuration.")

if __name__ == "__main__":
    main()
