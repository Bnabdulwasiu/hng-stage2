from fastapi import HTTPException

#Helper functions
def error_response(status_code: int, message: str):
     raise HTTPException(
          status_code=status_code,
          detail={
               "status": "error",
               "message": message
          }
     )


def get_age_group(age: int | None) -> str | None:
    if age is None:
        return None
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"
