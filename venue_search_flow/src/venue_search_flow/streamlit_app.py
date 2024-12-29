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
    if 'report_path' in st.session_state:
        del st.session_state['report_path']

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

def load_report(report_path):
    """Load and return the report data"""
    try:
        with open(report_path) as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading report: {str(e)}")
        return None

def display_report_section():
    """Display the report section if available"""
    if 'report_path' in st.session_state and 'output_dir' in st.session_state:
        st.write("### 📊 Generated Report")
        
        report_data = load_report(st.session_state.report_path)
        if report_data:
            # Display summary
            st.write("#### Summary")
            summary = report_data.get('summary', {})
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Venues Found", summary.get('venues_found', 0))
            with col2:
                st.metric("Emails Generated", summary.get('emails_generated', 0))
            
            # Display venues
            if venues := report_data.get('analysis', {}).get('venues', []):
                st.write("#### 🏢 Analyzed Venues")
                for venue in venues:
                    with st.expander(f"📍 {venue['basic_info']['name']}"):
                        # Basic Info
                        st.write("##### Basic Information")
                        st.write(f"- **Type:** {venue['basic_info']['type']}")
                        st.write(f"- **Address:** {venue['basic_info']['address']}")
                        st.write(f"- **Distance:** {venue['basic_info']['distance_km']}km")
                        
                        # Features
                        if features := venue.get('features', {}).get('features', {}):
                            st.write("##### Features")
                            for feature_name, feature_data in features.items():
                                st.write(f"- **{feature_name.replace('_', ' ').title()}:** {feature_data.get('value', '')}")
                        
                        # Score
                        if score := venue.get('score', {}):
                            st.write("##### Scoring")
                            st.write(f"- **Total Score:** {score.get('total_score', 0)}/100")
                            if category_scores := score.get('category_scores', {}):
                                st.write("**Category Scores:**")
                                for category, cat_score in category_scores.items():
                                    st.write(f"  - {category.replace('_', ' ').title()}: {cat_score}")
                            if recommendations := score.get('recommendations', []):
                                st.write("**Recommendations:**")
                                for rec in recommendations:
                                    st.write(f"  - {rec}")
            
            # Display email templates
            if email_templates := report_data.get('analysis', {}).get('email_templates', []):
                st.write("#### 📧 Generated Emails")
                for template in email_templates:
                    email_path = Path(st.session_state.output_dir) / "emails" / f"{template['venue_id']}_email.txt"
                    if email_path.exists():
                        with st.expander(f"Email for {template['venue_id']}"):
                            st.write(f"**Subject:** {template['subject']}")
                            st.write(f"**Recipient:** {template['recipient']}")
                            st.write("**Body:**")
                            with open(email_path) as f:
                                st.code(f.read(), language='text')
                            st.write(f"**Follow-up Date:** {template['follow_up_date']}")
            
            # Display recommendations
            if recommendations := report_data.get('recommendations', ''):
                st.write("#### 💡 Overall Recommendations")
                # Split by semicolon and filter out empty strings
                recs = [rec.strip() for rec in recommendations.split(';') if rec.strip()]
                if recs:
                    for rec in recs:
                        st.write(f"- {rec}")
                else:
                    st.info("No specific recommendations available yet.")
            
            # Display visualizations if available
            if visualizations := report_data.get('visualizations', []):
                st.write("#### 📈 Visualizations")
                for viz_path in visualizations:
                    viz_file = Path(st.session_state.output_dir) / viz_path
                    if viz_file.exists():
                        st.image(str(viz_file))

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

        # API key validation
        api_keys_set = True
        openai_key = os.getenv("OPENAI_API_KEY")
        serper_key = os.getenv("SERPER_API_KEY")
        
        if not openai_key and not st.session_state.get('openai_key_input'):
            st.warning("⚠️ OpenAI API key not found. Please enter it in the sidebar.")
            api_keys_set = False
        
        if not serper_key:
            st.warning("⚠️ Serper API key not found. Please set the SERPER_API_KEY environment variable.")
            api_keys_set = False

    with col2:
        # Progress tracking
        st.write("### Progress")
        progress_bar = st.progress(0.0, "Ready to start")

    # Search button - placed below both columns
    if st.button("🔍 Start Search", disabled=not api_keys_set or not address, type="primary"):
        if address and api_keys_set:
            try:
                with st.spinner("Searching for venues..."):
                    # Execute search with user inputs
                    result = kickoff(
                        address=address,
                        radius_km=radius_km
                    )
                
                # Update progress and state
                st.session_state.output_dir = result['output_dir']
                st.session_state.report_path = result['report_path']
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

        # OpenAI API Key input
        st.subheader("API Configuration")
        openai_key_input = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="Enter your OpenAI API key",
            help="Enter your OpenAI API key to use this tool",
            key="openai_key_input"
        )
        
        if openai_key_input:
            os.environ["OPENAI_API_KEY"] = openai_key_input
            st.success("OpenAI API key set! ✅")

if __name__ == "__main__":
    main()