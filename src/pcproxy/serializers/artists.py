from pydantic import BaseModel
from pydantic import Field
from pydantic.alias_generators import to_snake


class SimilarArtistMatch(BaseModel):
    artistIdMatch: str
    rank: int

    class Config:
        alias_generator = to_snake
        populate_by_name = True
        extra = "forbid"


class SimilarArtistsApiParams(BaseModel):
    artistId: str | None = None
    callId: str | None = None

    class Config:
        alias_generator = to_snake
        populate_by_name = True
        extra = "forbid"


class SimilarArtistsResponse(BaseModel):
    similarArtists: list[SimilarArtistMatch] = Field(default_factory=list)
    params: SimilarArtistsApiParams

    class Config:
        alias_generator = to_snake
        populate_by_name = True
        extra = "forbid"
