from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from ..base import Base

class Users(Base):
    __tablename__ = "Users"

    ID = Column(Integer, primary_key=True, autoincrement=True, comment="사용자 고유 ID")
    Username = Column(String(50), unique=True, nullable=False, comment="사용자명 (로그인 ID)")
    Password = Column(String(255), nullable=False, comment="비밀번호")
    Role = Column(String(20), default="코디", comment="사용자 역할 (관리자, 코디, 의사)")
    Access_Token = Column(String(500), nullable=True, comment="JWT 액세스 토큰")
    Refresh_Token = Column(String(500), nullable=True, comment="JWT 리프레시 토큰")
    Token_Expires_At = Column(DateTime, nullable=True, comment="토큰 만료 시간")
    Last_Login_At = Column(DateTime, nullable=True, comment="마지막 로그인 시간")
