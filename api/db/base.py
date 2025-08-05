from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base

# 메타데이터
metadata = MetaData()

# Base 클래스 생성
Base = declarative_base(metadata=metadata)