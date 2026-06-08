import asyncio
from unittest.mock import AsyncMock
from unittest.mock import patch

from fastapi.testclient import TestClient

from pcproxy.connectors.recommendation import RecommendationException
from pcproxy.main import app


client = TestClient(app)

ARTIST_ID = "26b287fe-057c-42c6-bae7-40382f2ed5bf"


class SimilarArtistsTest:
    route = f"/native/v1/artists/{ARTIST_ID}/similar"

    def test_minimal(self):
        class BackendMock:
            get_similar_artists = AsyncMock(
                return_value={
                    "similarArtists": [],
                    "params": {
                        "artistId": ARTIST_ID,
                        "callId": "dc78c12c-ada1-4fc1-8cdb-2a7d40afa99f",
                    },
                },
            )

        with patch("pcproxy.routes.artists.RecommendationBackend", BackendMock):
            response = client.get(self.route)
            assert response.status_code == 200
            BackendMock.get_similar_artists.assert_called_once_with(artist_id=ARTIST_ID)

        assert response.json() == {
            "similar_artists": [],
            "params": {
                "artist_id": ARTIST_ID,
                "call_id": "dc78c12c-ada1-4fc1-8cdb-2a7d40afa99f",
            },
        }

    def test_full(self):
        class BackendMock:
            get_similar_artists = AsyncMock(
                return_value={
                    "similarArtists": [
                        {"artistIdMatch": "a5712e68-cb1f-4f3b-82b5-ed36379f1b2d", "rank": 1},
                        {"artistIdMatch": "a09bd848-c9ec-4648-8be2-1dcf03c16715", "rank": 2},
                    ],
                    "params": {
                        "artistId": ARTIST_ID,
                        "callId": "dc78c12c-ada1-4fc1-8cdb-2a7d40afa99f",
                    },
                },
            )

        with patch("pcproxy.routes.artists.RecommendationBackend", BackendMock):
            response = client.get(self.route)
            assert response.status_code == 200
            BackendMock.get_similar_artists.assert_called_once_with(artist_id=ARTIST_ID)

        assert response.json() == {
            "similar_artists": [
                {"artist_id_match": "a5712e68-cb1f-4f3b-82b5-ed36379f1b2d", "rank": 1},
                {"artist_id_match": "a09bd848-c9ec-4648-8be2-1dcf03c16715", "rank": 2},
            ],
            "params": {
                "artist_id": ARTIST_ID,
                "call_id": "dc78c12c-ada1-4fc1-8cdb-2a7d40afa99f",
            },
        }

    def test_invalid_artist_id(self):
        class BackendMock:
            get_similar_artists = AsyncMock()

        with patch("pcproxy.routes.artists.RecommendationBackend", BackendMock):
            response = client.get("/native/v1/artists/not-a-uuid/similar")
            BackendMock.get_similar_artists.assert_not_called()

        assert response.status_code == 400

    def test_timeout(self):
        class BackendMock:
            get_similar_artists = AsyncMock(side_effect=asyncio.TimeoutError)

        with patch("pcproxy.routes.artists.RecommendationBackend", BackendMock):
            response = client.get(self.route)
            assert response.status_code == 504

        assert response.json() == {"code": "RECOMMENDATION_API_TIMEOUT"}

    def test_backend_unavailable(self):
        class BackendMock:
            get_similar_artists = AsyncMock(side_effect=RecommendationException)

        with patch("pcproxy.routes.artists.RecommendationBackend", BackendMock):
            response = client.get(self.route)
            assert response.status_code == 502

        assert response.json() == {"code": "RECOMMENDATION_API_ERROR"}
