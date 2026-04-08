import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# Get DATABASE_URL from the environment variable, fallback to default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@bonnetjes-app-backend-postgresql:5432/receipts")
# DATABASE_URL = "postgresql://user:password@localhost/receipts"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


