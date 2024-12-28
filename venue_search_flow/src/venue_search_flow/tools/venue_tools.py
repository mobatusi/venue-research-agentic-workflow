from crewai.tools import BaseTool
from typing import Dict, List
import json

class VenueScoringAlgorithm(BaseTool):
    name: str = "VenueScoringAlgorithm"
    description: str = "Calculate venue scores based on multiple criteria"
    
    async def run(self, criteria: dict) -> dict:
        """Score venue based on weighted criteria"""
        weights = {
            "location": 0.25,
            "facilities": 0.35,
            "operations": 0.25,
            "cost_value": 0.15
        }
        
        score = sum(
            criteria.get(category, 0) * weight 
            for category, weight in weights.items()
        )
        
        return {
            "total_score": score,
            "category_scores": {
                category: criteria.get(category, 0)
                for category in weights.keys()
            }
        }

class PricingAnalyzer(BaseTool):
    name: str = "PricingAnalyzer"
    description: str = "Analyze venue pricing and value propositions"
    
    async def run(self, venue_data: dict) -> dict:
        """Analyze venue pricing and included services"""
        base_price = venue_data.get("price", 0)
        included_services = venue_data.get("included_services", [])
        
        return {
            "price_analysis": {
                "base_price": base_price,
                "included_services": included_services,
                "value_score": len(included_services) * 0.1 * base_price
            }
        }

class EmailTemplateTool(BaseTool):
    name: str = "EmailTemplateTool"
    description: str = "Generate personalized email templates"
    
    async def run(self, venue_data: dict) -> str:
        """Generate personalized email template"""
        template = f"""
Subject: Event Space Inquiry - {venue_data.get('name', '')}

Dear {venue_data.get('contact_name', 'Venue Manager')},

I am writing to inquire about hosting an event at {venue_data.get('name', '')}. 
We are particularly interested in your {venue_data.get('highlight_features', [])} 
for our upcoming event.

Could we schedule a time to discuss the possibilities?

Best regards,
Event Planning Team
        """
        return template.strip()

class ContactEnrichmentAPI(BaseTool):
    name: str = "ContactEnrichmentAPI"
    description: str = "Enrich contact information for venues"
    
    async def run(self, contact_data: dict) -> dict:
        """Enrich contact information with additional details"""
        base_info = {
            "name": contact_data.get("name", ""),
            "email": contact_data.get("email", ""),
            "phone": contact_data.get("phone", "")
        }
        
        # Add enriched information
        enriched = {
            **base_info,
            "role": "Venue Manager",
            "response_rate": "95%",
            "preferred_contact": "email",
            "timezone": "UTC-5"
        }
        
        return enriched 