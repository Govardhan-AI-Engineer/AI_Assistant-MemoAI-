"""
Shared database base for all models
Ensures all models use the same declarative base
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
