from typing import List

from venue_score_flow.types import Venue, VenueScore, ScoredVenues


def combine_venues_with_scores(
    venues: List[Venue], venue_scores: List[VenueScore]
) -> List[ScoredVenues]:
    """
    Combine the venues with their scores using a dictionary for efficient lookups.
    """
    print("COMBINING VENUES WITH SCORES")
    print("SCORES:", venue_scores)
    print("VENUES:", venues)
    
    score_dict = {score.name.strip().lower(): score for score in venue_scores}
    print("SCORE DICT:", score_dict)

    scored_venues = []
    for venue in venues:
        normalized_name = venue.name.strip().lower()
        print(f"Processing venue: {venue.name}, Normalized: {normalized_name}")
        score = score_dict.get(normalized_name)
        if score:
            scored_venues.append(
                ScoredVenues(
                    id=venue.id,
                    name=venue.name,
                    type=venue.type,
                    address=venue.address,
                    distance_km=venue.distance_km,
                    website=venue.website or "",
                    phone=venue.phone or "",
                    email=venue.email or "",
                    score=score.score,
                    reason=score.reason,
                )
            )
        else:
            print(f"No score found for venue: {venue.name}")

    print("SCORED VENUES:", scored_venues)
    return scored_venues
