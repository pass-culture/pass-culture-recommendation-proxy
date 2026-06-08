import asyncio
import uuid

import fastapi

from pcproxy.connectors.recommendation import RecommendationBackend
from pcproxy.connectors.recommendation import RecommendationException
from pcproxy.main import app
from pcproxy.serializers import artists as serializers
from pcproxy.serializers.error import SimpleError


@app.get("/native/v1/artists/{artist_id}/similar")
async def similar_artists(
    artist_id: str,
    response: fastapi.Response,
) -> serializers.SimilarArtistsResponse | SimpleError:
    """Proxy pass-through to the Data Science recommendation API.

    Returns the raw DS response:
        {"similar_artists": [{"artist_id_match": "<uuid>", "rank": <int>}], "params": {...}}

    This endpoint does NOT enrich results with artist metadata (name, image) and does NOT
    filter out blacklisted artists or artists without eligible offers. That enrichment
    is performed by pass-culture-main's homonymous route when called directly.

    On DS API failure: 502 (RECOMMENDATION_API_ERROR) or 504 (RECOMMENDATION_API_TIMEOUT).
    On invalid artist_id (non-UUID): 400.
    """
    try:
        uuid.UUID(artist_id)
    except ValueError as exc:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="Invalid artist_id"
        ) from exc

    try:
        result = await RecommendationBackend().get_similar_artists(artist_id=artist_id)
    except asyncio.TimeoutError:
        response.status_code = fastapi.status.HTTP_504_GATEWAY_TIMEOUT
        return SimpleError(code="RECOMMENDATION_API_TIMEOUT")
    except RecommendationException:
        response.status_code = fastapi.status.HTTP_502_BAD_GATEWAY
        return SimpleError(code="RECOMMENDATION_API_ERROR")
    return serializers.SimilarArtistsResponse(**result)
