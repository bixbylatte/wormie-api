from enum import StrEnum


class ShareMode(StrEnum):
    TRADE = "TRADE"
    LEND = "LEND"


class ListingStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    ARCHIVED = "ARCHIVED"


class RequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RETURNED = "RETURNED"
    COMPLETED = "COMPLETED"

