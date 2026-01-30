"""
Simple authentication service with user registration and login
Uses SQLite and secure password hashing
"""
import hashlib
import secrets
from typing import Optional, Tuple
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from src.core.config import Config
from src.core.database import Base


class User(Base):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class AuthService:
    """
    Simple authentication service with user registration and login
    Uses secure password hashing (PBKDF2 with SHA-256)
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize authentication service
        
        Args:
            database_url: Database URL (defaults to Config.DATABASE_URL)
        """
        self.database_url = database_url or Config.DATABASE_URL
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(self.engine)
    
    def _hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash password using PBKDF2 with SHA-256
        
        Args:
            password: Plain text password
            salt: Optional salt (generates new one if None)
            
        Returns:
            Tuple of (password_hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)  # 64 character hex string
        
        # Use PBKDF2 with SHA-256
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100k iterations
        )
        
        return password_hash.hex(), salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """
        Verify password against stored hash
        
        Args:
            password: Plain text password to verify
            password_hash: Stored password hash
            salt: Stored salt
            
        Returns:
            True if password matches, False otherwise
        """
        computed_hash, _ = self._hash_password(password, salt)
        return computed_hash == password_hash
    
    def register_user(self, username: str, password: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Register a new user
        
        Args:
            username: Username (must be unique)
            password: Plain text password
            
        Returns:
            Tuple of (success, user_id, error_message)
            - success: True if registration successful
            - user_id: User ID if successful, None otherwise
            - error_message: Error message if failed, None if successful
        """
        if not username or not username.strip():
            return False, None, "Username cannot be empty"
        
        if not password or len(password) < 6:
            return False, None, "Password must be at least 6 characters"
        
        db: Session = self.SessionLocal()
        try:
            # Check if username already exists
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                return False, None, "Username already exists"
            
            # Hash password
            password_hash, salt = self._hash_password(password)
            
            # Create new user
            new_user = User(
                username=username.strip(),
                password_hash=password_hash,
                salt=salt
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            return True, new_user.id, None
            
        except Exception as e:
            db.rollback()
            return False, None, f"Registration failed: {str(e)}"
        finally:
            db.close()
    
    def login_user(self, username: str, password: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Authenticate user and return user ID
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Tuple of (success, user_id, error_message)
            - success: True if login successful
            - user_id: User ID if successful, None otherwise
            - error_message: Error message if failed, None if successful
        """
        if not username or not password:
            return False, None, "Username and password are required"
        
        db: Session = self.SessionLocal()
        try:
            # Find user
            user = db.query(User).filter(User.username == username).first()
            
            if not user:
                return False, None, "Invalid username or password"
            
            if not user.is_active:
                return False, None, "User account is inactive"
            
            # Verify password
            if not self._verify_password(password, user.password_hash, user.salt):
                return False, None, "Invalid username or password"
            
            return True, user.id, None
            
        except Exception as e:
            return False, None, f"Login failed: {str(e)}"
        finally:
            db.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """
        Get user information by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User dictionary with id, username, created_at, or None if not found
        """
        db: Session = self.SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            return {
                'id': user.id,
                'username': user.username,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'is_active': user.is_active
            }
        finally:
            db.close()
    
    def user_exists(self, username: str) -> bool:
        """
        Check if username exists
        
        Args:
            username: Username to check
            
        Returns:
            True if username exists, False otherwise
        """
        db: Session = self.SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            return user is not None
        finally:
            db.close()
