from fastapi import HTTPException


class TLEFetchError(Exception):
    def __init__(self, group: str, detail: str = ""):
        self.group = group
        self.detail = detail
        super().__init__(f"Failed to fetch TLE group '{group}': {detail}")


class CacheError(Exception):
    def __init__(self, operation: str, detail: str = ""):
        self.operation = operation
        self.detail = detail
        super().__init__(f"Cache {operation} failed: {detail}")


class SatelliteNotFoundError(HTTPException):
    def __init__(self, name: str):
        super().__init__(status_code=404, detail=f"Satellite '{name}' not found")
