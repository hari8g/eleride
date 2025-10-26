from fastapi import HTTPException


def ensure_not_none(value, message: str):
    if value is None:
        raise HTTPException(status_code=404, detail=message)
    return value


