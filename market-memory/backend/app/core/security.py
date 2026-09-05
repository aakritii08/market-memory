from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings
pwd=CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(p): return pwd.hash(p)
def verify_password(p,h): return pwd.verify(p,h)
def create_token(user_id:int): return jwt.encode({"sub":str(user_id),"exp":datetime.now(timezone.utc)+timedelta(minutes=settings.jwt_exp_minutes)},settings.jwt_secret,algorithm="HS256")
def decode_token(token): return jwt.decode(token,settings.jwt_secret,algorithms=["HS256"])
