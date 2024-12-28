import asyncio
from venue_search_flow import VenueSearchFlow
from helper import get_openai_api_key, get_serper_api_key
import os

async def main():
    # Set API keys
    os.environ["OPENAI_API_KEY"] = get_openai_api_key()
    os.environ["SERPER_API_KEY"] = get_serper_api_key()
    
    # Create and run the flow
    flow = VenueSearchFlow()
    
    # Example usage
    result = await flow.kickoff(
        address="123 Main St, San Francisco, CA 94105",
        radius_km=5.0
    )
    
    print("\nFinal Report:")
    print(result)
    
    # Optionally generate a visualization of the flow
    flow.plot("venue_search_flow")

if __name__ == "__main__":
    asyncio.run(main()) 