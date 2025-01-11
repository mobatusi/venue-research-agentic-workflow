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
    # Create a dictionary to map score IDs to their corresponding VenueScore objects
    score_dict = {score.id: score for score in venue_scores}
    print("SCORE DICT:", score_dict)

    scored_venues = []
    for venue in venues:
        score = score_dict.get(venue.id)
        if score:
            scored_venues.append(
                ScoredVenues(
                    id=venue.id,
                    name=venue.name,
                    type=venue.type,
                    address=venue.address,
                    distance_km=venue.distance_km,
                    website=venue.website,
                    phone=venue.phone,
                    email=venue.email,
                    capacity=venue.capacity,
                    amenities=venue.amenities,
                    accessibility=venue.accessibility,
                    parking=venue.parking,
                    special_features=venue.special_features,
                    audio_visual=venue.audio_visual,
                    technology=venue.technology,
                    other=venue.other,
                    score=score.score,
                    reason=score.reason,
                )
            )

    print("SCORED VENUES:", scored_venues)
    return scored_venues
