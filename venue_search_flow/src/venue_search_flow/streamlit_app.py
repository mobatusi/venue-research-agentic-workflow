import streamlit as st
import os
import json
from pathlib import Path
from venue_search_flow.main import kickoff
from datetime import datetime, timedelta
import datetime as dt

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
                    # Try to parse the raw email data as list
                    if isinstance(report_data["emails_data"], str):
                        raw_email = [json.loads(report_data["emails_data"])]
                    else:
                        raw_email = [report_data["emails_data"]]
                    if isinstance(raw_email, list):
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

        # Email Template Configuration
        st.subheader("Email Template")
        use_custom_template = st.checkbox("Use Custom Email Template", 
                                        help="Toggle to use your own email template instead of the default one",
                                        key="use_custom_template")

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
    
    # Check if either key is missing or empty
    has_openai_key = bool(openai_key_input.strip())  # Only consider session state input
    has_serper_key = bool(serper_key_input.strip())  # Only consider session state input
    
    if not has_openai_key:
        st.warning("⚠️ OpenAI API key not found. Please enter it in the sidebar.")
    
    if not has_serper_key:
        st.warning("⚠️ Serper API key not found. Please enter it in the sidebar.")

    if use_custom_template:
        # Template Variables Form
        st.subheader("Template Variables")
        with st.form("template_variables"):
            sender_name = st.text_input(
                "Sender Name",
                value=st.session_state.get('sender_name', 'John Smith'),
                help="Your name as it will appear in the email",
                key="sender_name_input"
            )
            
            custom_message = st.text_area(
                "Custom Message",
                value=st.session_state.get('custom_message', 'We are planning a corporate event for 100 attendees, focusing on team building and professional development. We are particularly interested in venues that can accommodate both presentation-style seating and breakout session areas.'),
                help="Additional details about your event or specific requirements",
                height=100,
                key="custom_message_input"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                # Set default date to 3 months from now
                default_date = datetime.now() + timedelta(days=90)
                target_date = st.date_input(
                    "Event Date",
                    value=st.session_state.get('target_date', default_date),
                    help="Target date for your event",
                    key="target_date_input"
                )
            
            with col2:
                # Set default time to 2 PM
                default_time = dt.time(14, 0)  # 2:00 PM
                target_time = st.time_input(
                    "Event Time",
                    value=st.session_state.get('target_time', default_time),
                    help="Target time for your event",
                    key="target_time_input"
                )
            
            st.subheader("Social Media Links")
            linkedin_link = st.text_input(
                "LinkedIn Profile",
                value=st.session_state.get('linkedin_link', 'https://www.linkedin.com/in/your-profile'),
                help="Your LinkedIn profile URL",
                key="linkedin_link_input"
            )
            
            instagram_link = st.text_input(
                "Instagram Profile",
                value=st.session_state.get('instagram_link', 'https://www.instagram.com/your-profile'),
                help="Your Instagram profile URL",
                key="instagram_link_input"
            )
            
            tiktok_link = st.text_input(
                "TikTok Profile",
                value=st.session_state.get('tiktok_link', 'https://www.tiktok.com/@your-profile'),
                help="Your TikTok profile URL",
                key="tiktok_link_input"
            )
            
            if st.form_submit_button("Save Template Variables"):
                st.session_state.sender_name = sender_name
                st.session_state.custom_message = custom_message
                st.session_state.target_date = target_date
                st.session_state.target_time = target_time
                st.session_state.linkedin_link = linkedin_link
                st.session_state.instagram_link = instagram_link
                st.session_state.tiktok_link = tiktok_link
                
                # Update the template with current values
                try:
                    # Format date and time
                    date_str = target_date.strftime('%Y-%m-%d') if target_date else '[EVENT DATE]'
                    time_str = target_time.strftime('%I:%M %p') if target_time else '[EVENT TIME]'
                    
                    # Update the template in session state with current values
                    current_template = st.session_state.get('custom_template', '')
                    if current_template:
                        updated_template = current_template.format(
                            sender_name=sender_name,
                            custom_message=custom_message,
                            target_date=date_str,
                            target_time=time_str,
                            linkedin_link=linkedin_link or '[LinkedIn Profile]',
                            instagram_link=instagram_link or '[Instagram Profile]',
                            tiktok_link=tiktok_link or '[TikTok Profile]',
                            contact_name='[Venue Contact]',
                            venue_name='[Venue Name]'
                        )
                        st.session_state.custom_template = updated_template
                    st.success("✅ Template variables saved and preview updated!")
                except Exception as e:
                    st.error(f"Could not update template preview: {str(e)}")
                    st.info("Make sure your template includes all the required placeholders and they are properly formatted.")

        custom_template = st.text_area(
            "Custom Email Template",
            value=st.session_state.get('custom_template', """Dear {contact_name},

I hope this email finds you well. I am reaching out regarding potential venue space at {venue_name} for an event on {target_date} at {target_time}.

{custom_message}

I would greatly appreciate the opportunity to discuss:
- Available event spaces and capacity
- Pricing and packages
- Catering options
- Audio/visual capabilities
- Available dates
                                           
Below is a link to our LinkedIn, Instagram, and TikTok profiles, which should give you an idea of the style of the events. 
- LinkedIn: {linkedin_link}
- Instagram: {instagram_link}
- TikTok: {tiktok_link}

Please let me know when would be a good time to connect.

Best regards,
{sender_name}"""),
            height=300,
            help="Use placeholders like {venue_name}, {contact_name}, {custom_message}, {sender_name}, {target_date}, {target_time}, {linkedin_link}, {instagram_link}, {tiktok_link} in your template. The template will be updated with your values when you save the variables above.",
            key="custom_template"
        )

        if custom_template != st.session_state.get('custom_template', ''):
            st.session_state.custom_template = custom_template
            st.info("Template updated. Save the template variables above to see it with your values.")
    else:
        st.info("Using default system email template")

    # Search button - placed below both columns
    search_disabled = not address or not has_openai_key or not has_serper_key
    
    if st.button("🔍 Start Search", disabled=search_disabled, type="primary"):
        if address and has_openai_key and has_serper_key:
            try:
                with st.spinner("Searching for venues..."):
                    # Set API keys from session state
                    os.environ["OPENAI_API_KEY"] = openai_key_input
                    os.environ["SERPER_API_KEY"] = serper_key_input
                    
                    # Prepare email template with variables if custom template is used
                    final_template = None
                    if use_custom_template:
                        template = st.session_state.get('custom_template', '')
                        if template:
                            # Format date and time
                            date_str = st.session_state.get('target_date', '').strftime('%Y-%m-%d') if st.session_state.get('target_date') else ''
                            time_str = st.session_state.get('target_time', '').strftime('%I:%M %p') if st.session_state.get('target_time') else ''
                            
                            # Replace variables in template
                            final_template = template.format(
                                sender_name=st.session_state.get('sender_name', ''),
                                custom_message=st.session_state.get('custom_message', ''),
                                target_date=date_str,
                                target_time=time_str,
                                linkedin_link=st.session_state.get('linkedin_link', ''),
                                instagram_link=st.session_state.get('instagram_link', ''),
                                tiktok_link=st.session_state.get('tiktok_link', ''),
                                contact_name='{contact_name}',  # Keep these as placeholders
                                venue_name='{venue_name}'      # for the kickoff function
                            )
                    
                    # Execute search with user inputs
                    result = kickoff(
                        address=address,
                        radius_km=radius_km,
                        email_template=final_template if use_custom_template else None
                    )
                
                # Update progress and state
                st.session_state.output_dir = result['output_dir']
                update_progress(progress_bar, result['current_step'], result['progress'])
                
                if result['current_step'] == 'completed':
                    st.success("✅ Search completed successfully!")
                
            except Exception as e:
                st.error(f"❌ An error occurred during the search: {str(e)}")
                st.exception(e)
            
    # Download buttons for generated files
    if st.session_state.get('output_dir'):
        col1, col2 = st.columns(2)
        
        with col1:
            # Email download button
            email_path = os.path.join(st.session_state.output_dir, "emails")
            if os.path.exists(email_path):
                email_files = [f for f in os.listdir(email_path) if f.endswith('.txt')]
                if email_files:
                    with open(os.path.join(email_path, email_files[0]), 'r') as f:
                        email_content = f.read()
                    st.download_button(
                        label="📥 Download Generated Email",
                        data=email_content,
                        file_name="venue_outreach_email.txt",
                        mime="text/plain"
                    )
        
        with col2:
            # Report download button
            report_path = os.path.join(st.session_state.output_dir, "reports")
            if os.path.exists(report_path):
                report_files = [f for f in os.listdir(report_path) if f.endswith('.json')]
                if report_files:
                    with open(os.path.join(report_path, report_files[0]), 'r') as f:
                        report_content = f.read()
                    st.download_button(
                        label="📥 Download Generated Report",
                        data=report_content,
                        file_name="venue_analysis_report.json",
                        mime="application/json"
                    )

    # Display report section
    display_report_section()

if __name__ == "__main__":
    main()