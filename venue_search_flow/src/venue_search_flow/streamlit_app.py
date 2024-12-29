import streamlit as st
import os
import json
from pathlib import Path
from venue_search_flow.main import kickoff
import time

def reset_progress():
    """Reset the progress status"""
    if 'progress_value' in st.session_state:
        del st.session_state.progress_value
    if 'current_step' in st.session_state:
        del st.session_state.current_step
    if 'output_dir' in st.session_state:
        del st.session_state['output_dir']

def update_progress(progress_bar, step: str, progress: float):
    """Update progress bar and step description"""
    steps = {
        'initialization': '🚀 Initializing search...',
        'location_analysis': '📍 Analyzing location...',
        'feature_extraction': '🔍 Extracting features...',
        'scoring': '⭐ Scoring venues...',
        'report_generation': '📊 Generating report...',
        'completed': '✅ Search completed!'
    }
    
    message = steps.get(step, step)
    progress_bar.progress(progress, message)

def display_report_section():
    """Display the report section if available"""
    if "output_dir" in st.session_state:
        st.header("📊 Search Results")
        
        # Get the report directory
        report_dir = Path(st.session_state.output_dir) / "reports"
        report_path = report_dir / "report_generation_output.json"
        
        if report_path.exists():
            with open(report_path) as f:
                report_data = json.load(f)
            
            # Display summary metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Venues Found", report_data.get("venues_found", 0))
            with col2:
                st.metric("Emails Generated", report_data.get("emails_generated", 0))
            
            # Display venue details
            if "venues_data" in report_data:
                try:
                    # Parse the venues_data string into a list of dictionaries
                    venues_data = report_data["venues_data"]
                    
                    # Handle string format
                    if isinstance(venues_data, str):
                        try:
                            venues_data = json.loads(venues_data)
                        except json.JSONDecodeError as e:
                            st.error(f"Error parsing venues data: {str(e)}")
                            return
                    
                    # Convert to list if it's a single venue
                    if isinstance(venues_data, dict):
                        venues_data = [venues_data]
                    
                    if venues_data:
                        st.subheader("📍 Venue Details")
                        for venue in venues_data:
                            try:
                                venue_id = venue.get('venue_id', 'unknown')
                                venue_score = venue.get('venue_score', 'N/A')
                                key_features = venue.get('key_features', '').split(',')
                                
                                # Format venue name from venue_id
                                venue_name = ' '.join(venue_id.replace('_', ' ').title().split())
                                
                                # Get basic info
                                basic_info = venue.get('basic_info', {})
                                if isinstance(basic_info, str):
                                    try:
                                        basic_info = json.loads(basic_info)
                                    except json.JSONDecodeError:
                                        basic_info = {}
                                
                                with st.expander(f"🏢 {venue_name}"):
                                    # Basic Info
                                    st.write("**Basic Information**")
                                    st.write(f"- Name: {venue_name}")
                                    st.write(f"- Type: {basic_info.get('type', 'Hotel & Conference Center')}")
                                    st.write(f"- Address: {basic_info.get('address', '333 Adams St, Brooklyn, NY 11201')}")
                                    st.write(f"- Distance: {basic_info.get('distance_km', '0.0')} km")
                                    st.write(f"- Website: {basic_info.get('website', 'https://www.marriott.com/hotels/travel/nycbk-new-york-marriott-at-the-brooklyn-bridge/')}")
                                    
                                    # Contact info
                                    contact_info = basic_info.get('contact_info', {})
                                    if isinstance(contact_info, str):
                                        try:
                                            contact_info = json.loads(contact_info)
                                        except json.JSONDecodeError:
                                            contact_info = {}
                                            
                                    phone = contact_info.get('phone', basic_info.get('phone', '(718) 246-7000'))
                                    email = contact_info.get('email', basic_info.get('email', 'contact@brooklynmarriott.com'))
                                    st.write(f"- Phone: {phone}")
                                    st.write(f"- Email: {email}")
                                    st.write(f"- Score: {venue_score}/100")
                                    
                                    # Key Features
                                    if key_features:
                                        st.write("**Key Features**")
                                        for feature in key_features:
                                            if feature.strip():
                                                st.write(f"- {feature.strip()}")
                            except Exception as venue_e:
                                st.warning(f"Error displaying venue: {str(venue_e)}")
                                st.json(venue)
                except Exception as e:
                    st.error(f"Error processing venues data: {str(e)}")
                    st.json(report_data["venues_data"])
            
            # Display recommendations
            if "recommendations" in report_data and report_data["recommendations"]:
                st.subheader("💡 Overall Recommendations")
                recommendations = report_data["recommendations"].split(";")
                for rec in recommendations:
                    if rec.strip():
                        st.write(f"- {rec.strip()}")
            
            # Display generated emails
            if "emails_data" in report_data:
                try:
                    # Parse the emails_data string into a list of dictionaries
                    emails_data = json.loads(report_data["emails_data"])
                    if isinstance(emails_data, str):
                        emails_data = json.loads(emails_data)  # Parse again if still a string
                        
                    if emails_data:
                        st.subheader("📧 Generated Emails")
                        for email in emails_data:
                            if isinstance(email, str):
                                email = json.loads(email)  # Parse if the email is a string
                                
                            with st.expander(f"📨 Email for {email.get('venue_id', 'Unknown Venue')}"):
                                st.write(f"**Subject:** {email.get('subject', 'N/A')}")
                                st.write(f"**Recipient:** {email.get('recipient', 'N/A')}")
                                st.write(f"**Follow-up Date:** {email.get('follow_up_date', 'N/A')}")
                                st.write("**Content:**")
                                st.text_area("", email.get('body', 'N/A'), height=200, key=f"email_{email.get('venue_id')}")
                except Exception as e:
                    st.warning("Displaying raw email data:")
                    try:
                        # Try to parse the raw email data
                        if isinstance(report_data["emails_data"], str):
                            raw_email = json.loads(report_data["emails_data"])
                        else:
                            raw_email = report_data["emails_data"]
                            
                        if isinstance(raw_email, dict):
                            # Single email format
                            st.subheader("📧 Generated Email")
                            with st.expander("📨 Email Details"):
                                st.write(f"**Subject:** {raw_email.get('subject', 'N/A')}")
                                st.write(f"**Recipient:** {raw_email.get('recipient', 'N/A')}")
                                st.write(f"**Follow-up Date:** {raw_email.get('follow_up_date', 'N/A')}")
                                st.write("**Content:**")
                                st.text_area("", raw_email.get('body', 'N/A'), height=200, key="raw_email")
                        elif isinstance(raw_email, list):
                            # Multiple emails format
                            st.subheader("📧 Generated Emails")
                            for idx, email in enumerate(raw_email):
                                with st.expander(f"📨 Email {idx + 1}"):
                                    st.write(f"**Subject:** {email.get('subject', 'N/A')}")
                                    st.write(f"**Recipient:** {email.get('recipient', 'N/A')}")
                                    st.write(f"**Follow-up Date:** {email.get('follow_up_date', 'N/A')}")
                                    st.write("**Content:**")
                                    st.text_area("", email.get('body', 'N/A'), height=200, key=f"raw_email_{idx}")
                    except Exception as nested_e:
                        st.error(f"Could not parse email data: {str(nested_e)}")
                        st.json(report_data["emails_data"])
        else:
            st.info("No report available yet. Start a search to generate a report.")

def main():
    st.set_page_config(
        page_title="Venue Search Workflow",
        page_icon="🏢",
        layout="wide"
    )
    
    st.title("🏢 Venue Search Workflow")
    st.write("Enter an address and search radius to find and analyze venues in the area.")

    # Create main layout
    col1, col2 = st.columns([2, 1])

    with col1:
        # Input fields with more descriptive labels and help text
        address = st.text_input(
            "Search Location",
            value="333 Adams St, Brooklyn, NY 11201, United States",
            help="Enter the full address to search around (e.g., street, city, state, country)",
            key="address_input"
        )
        
        radius_km = st.slider(
            "Search Radius",
            min_value=0.1,
            max_value=1.0,
            value=0.5,
            step=0.1,
            help="Select the radius (in kilometers) around the location to search for venues",
            key="radius_input"
        )

    with col2:
        # Progress tracking
        st.write("### Progress")
        progress_bar = st.progress(0.0, "Ready to start")

    # API key validation
    openai_key = os.getenv("OPENAI_API_KEY", "")
    serper_key = os.getenv("SERPER_API_KEY", "")
    openai_key_input = st.session_state.get('openai_key_input', "")
    serper_key_input = st.session_state.get('serper_key_input', "")
    
    # Check if either key is missing or empty
    has_openai_key = bool(openai_key_input.strip())  # Only consider session state input
    has_serper_key = bool(serper_key_input.strip())  # Only consider session state input
    
    if not has_openai_key:
        st.warning("⚠️ OpenAI API key not found. Please enter it in the sidebar.")
    
    if not has_serper_key:
        st.warning("⚠️ Serper API key not found. Please enter it in the sidebar.")
    
    # Search button - placed below both columns
    search_disabled = not address or not has_openai_key or not has_serper_key
    
    if st.button("🔍 Start Search", disabled=search_disabled, type="primary"):
        if address and has_openai_key and has_serper_key:
            try:
                with st.spinner("Searching for venues..."):
                    # Set API keys from session state
                    os.environ["OPENAI_API_KEY"] = openai_key_input
                    os.environ["SERPER_API_KEY"] = serper_key_input
                    
                    # Execute search with user inputs
                    result = kickoff(
                        address=address,
                        radius_km=radius_km
                    )
                
                # Update progress and state
                st.session_state.output_dir = result['output_dir']
                update_progress(progress_bar, result['current_step'], result['progress'])
                
                if result['current_step'] == 'completed':
                    st.success("✅ Search completed successfully!")
                
            except Exception as e:
                st.error(f"❌ An error occurred during the search: {str(e)}")
                st.exception(e)

    # Display report section
    display_report_section()

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
            # value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            placeholder="Enter your OpenAI API key",
            help="Required for AI-powered analysis and content generation",
            key="openai_key_input"
        )
        
        # Serper API Key input
        serper_key_input = st.text_input(
            "Serper API Key",
            # value=os.getenv("SERPER_API_KEY", ""),
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

if __name__ == "__main__":
    main()