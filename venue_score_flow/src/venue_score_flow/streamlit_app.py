import streamlit as st
import asyncio
from venue_score_flow.main import run_with_inputs
from venue_score_flow.constants import EMAIL_TEMPLATE

def main():
    st.title("Venue Research Agentic Workflow")

    # Collect user inputs
    address = st.text_input("Address", "1333 Adams St, Brooklyn, NY 11201, United States")
    radius_km = st.number_input("Radius (km)", min_value=0.1, max_value=10.0, value=0.5)
    event_date = st.date_input("Event Date")
    linkedin_url = st.text_input("LinkedIn URL", "https://linkedin.com/company/mycompany")
    instagram_url = st.text_input("Instagram URL", "https://instagram.com/mycompany")
    tiktok_url = st.text_input("TikTok URL", "https://tiktok.com/@mycompany")
    sender_name = st.text_input("Sender Name", "John Doe")
    sender_email = st.text_input("Sender Email", "john.doe@example.com")
    email_template = st.text_area("Email Template", EMAIL_TEMPLATE)

    # Button to run the workflow
    if st.button("Run Venue Search"):
        inputs = {
            "address": address,
            "radius_km": radius_km,
            "event_date": event_date.strftime("%Y-%m-%d"),
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
            # Write results to JSON file
            with open('venue_search_results.json', 'w', encoding='utf-8') as f:
                f.write(result.model_dump_json(indent=2))
            st.success("Results written to venue_search_results.json")
        else:
            st.error("Failed to retrieve results. Please check the agent configuration.")

if __name__ == "__main__":
    main()
