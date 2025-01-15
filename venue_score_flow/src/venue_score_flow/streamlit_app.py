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
            2. 📊 Analyze the venues found
            3. 📝 Generate a detailed report
            4. 📧 Create outreach emails
            
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
    address = st.text_input(
        "Search Location",
        value="333 Adams St, Brooklyn, NY 11201, United States",
        help="Enter the full address to search around (e.g., street, city, state, country)",
        key="address_input"
    )
    
    radius_km = st.slider(
        "Search Radius",
        min_value=0.1,
        max_value=2.0,
        value=0.5,
        step=0.1,
        help="Select the radius (in kilometers) around the location to search for venues",
        key="radius_input"
    )
    
    # Set default date to 3 months from now
    default_date = datetime.now() + timedelta(days=90)
    target_date = st.date_input(
        "Event Date",
        value=st.session_state.get('target_date', default_date),
        help="Target date for your event",
        key="target_date_input"
    )

    # Set default time to 2 PM
    default_time = dt.time(14, 0)  # 2:00 PM
    target_time = st.time_input(
        "Event Time",
        value=st.session_state.get('target_time', default_time),
        help="Target time for your event",
        key="target_time_input"
    )

    # Format date and time
    event_date = target_date.strftime('%Y-%m-%d') if target_date else '[EVENT DATE]'
    event_time = target_time.strftime('%I:%M %p') if target_time else '[EVENT TIME]'

    # Add sender name and email input fields
    sender_name = st.text_input("Sender Name", sender_name)
    sender_email = st.text_input("Sender Email", sender_email)
                    
    # Use a checkbox to toggle the email template form
    use_custom_template = st.checkbox("Use Custom Email Template", 
                                       help="Toggle to use your own email template instead of the default one",
                                       key="use_custom_template")   

    if use_custom_template:
        # Show the form for custom email template input
        with st.form("template_variables"):
            st.subheader("Email Template Configuration")
            
            email_template = st.text_area("Email Template", email_template)
            
            # Add a submit button for the form
            if st.form_submit_button("Save Template"):
                st.session_state.email_template = email_template
                st.success("✅ Template variables saved and preview updated!")

    # Initialize social media links
    linkedin_url = ""
    instagram_url = ""
    tiktok_url = ""

    if use_custom_template:
        # Show social media input fields only if using a custom template
        st.subheader("Social Media Links")
        linkedin_url = st.text_input("LinkedIn URL", "https://linkedin.com/company/mycompany")
        instagram_url = st.text_input("Instagram URL", "https://instagram.com/mycompany")
        tiktok_url = st.text_input("TikTok URL", "https://tiktok.com/@mycompany")

    # Search button - placed below both columns
    search_disabled = not address or not event_date or not event_time or not sender_name or not sender_email or not email_template
    
    # Button to run the workflow
    if st.button("🔍 Start Search", disabled=search_disabled, type="primary"):
        if address and radius_km and event_date and event_time and sender_name and sender_email and email_template:
            try:
                with st.spinner("Searching for venues..."):
                    inputs = {
                        "address": address,
                        "radius_km": radius_km,
                        "event_date": event_date,
                        "event_time": event_time,
                        "linkedin_url": linkedin_url,
                        "instagram_url": instagram_url,
                        "tiktok_url": tiktok_url,
                        "sender_name": sender_name,
                        "sender_email": sender_email,
                        "email_template": email_template
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
            except Exception as e:
                st.error(f"❌ An error occurred during the search: {str(e)}")
                st.exception(e)

if __name__ == "__main__":
    main()
