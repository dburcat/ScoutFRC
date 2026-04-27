from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core import security
from app.crud import crud_user
from app.models.user import User
from app.schemas.token import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id: str | None = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
        # Create the payload object
        token_data = TokenPayload(sub=int(user_id))
        
        # Explicitly check token_data.sub here to satisfy the type-checker
        if token_data.sub is None:
            raise credentials_exception
            
    except (JWTError, ValueError):
        raise credentials_exception
        
    # 4. Use the validated ID to find the user
    user = crud_user.get_user_by_id(db, user_id=token_data.sub)
    if not user:
        raise credentials_exception
    return user