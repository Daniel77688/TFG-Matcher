"""
Sistema de autenticación y gestión de usuarios con SQLModel.
"""
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

import jwt
import bcrypt
from sqlmodel import SQLModel, Field, create_engine, Session, select, Relationship, delete

from src.config.config import DB_PATH, JWT_SECRET_KEY, JWT_EXPIRE_HOURS

logger = logging.getLogger(__name__)

# ========== MODELOS DE BASE DE DATOS ==========


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None

    profile: Optional["StudentProfile"] = Relationship(back_populates="user")
    history: List["SearchHistory"] = Relationship(back_populates="user")


class StudentProfile(SQLModel, table=True):
    __tablename__ = "student_profiles"

    user_id: Optional[int] = Field(default=None, foreign_key="users.id", primary_key=True)
    full_name: Optional[str] = None
    degree: Optional[str] = None
    year: Optional[int] = None
    interests: Optional[str] = None
    skills: Optional[str] = None
    preferred_areas: Optional[str] = None

    user: Optional[User] = Relationship(back_populates="profile")


class SearchHistory(SQLModel, table=True):
    __tablename__ = "search_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    query: str
    search_type: str = "general"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: Optional[User] = Relationship(back_populates="history")


# ========== SISTEMA DE AUTENTICACIÓN ==========


class AuthSystem:
    """Gestiona registro, login, perfiles y historial de búsquedas."""

    # Campos permitidos para actualización de perfil
    ALLOWED_PROFILE_FIELDS = frozenset(
        ["full_name", "degree", "year", "interests", "skills", "preferred_areas"]
    )

    def __init__(self, db_path: str = None):
        path = db_path or str(DB_PATH)
        self.db_url = f"sqlite:///{path}"
        self.engine = create_engine(self.db_url)
        self._init_database()

    def _init_database(self):
        """Inicializa las tablas de la base de datos."""
        SQLModel.metadata.create_all(self.engine)
        logger.info("Base de datos inicializada: %s", self.db_url)

    # ── Utilidades de hashing ──────────────────────────────────────

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def _verify_password(password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

    # ── JWT Tokens ─────────────────────────────────────────────────

    @staticmethod
    def create_access_token(user_id: int, username: str) -> str:
        """Genera un token JWT con expiración."""
        payload = {
            "user_id": user_id,
            "username": username,
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict]:
        """Verifica y decodifica un token JWT. Devuelve None si es inválido."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            return {"user_id": payload["user_id"], "username": payload["username"]}
        except jwt.ExpiredSignatureError:
            logger.warning("Token expirado")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Token inválido")
            return None

    # ── Validaciones ───────────────────────────────────────────────

    @staticmethod
    def validate_email(email: str) -> bool:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        if len(password) < 8:
            return False, "La contraseña debe tener al menos 8 caracteres"
        if not re.search(r"[A-Z]", password):
            return False, "La contraseña debe contener al menos una mayúscula"
        if not re.search(r"[a-z]", password):
            return False, "La contraseña debe contener al menos una minúscula"
        if not re.search(r"[0-9]", password):
            return False, "La contraseña debe contener al menos un número"
        return True, ""

    # ── Registro y Login ───────────────────────────────────────────

    def register(self, username: str, email: str, password: str) -> Dict:
        try:
            with Session(self.engine) as session:
                user = User(
                    username=username,
                    email=email,
                    password_hash=self._hash_password(password),
                )
                session.add(user)
                session.commit()
                session.refresh(user)

                # Crear perfil vacío
                profile = StudentProfile(user_id=user.id)
                session.add(profile)
                session.commit()

                return {
                    "success": True,
                    "message": "Usuario registrado exitosamente",
                    "user_id": user.id,
                    "username": user.username,
                }
        except Exception as e:
            if "UNIQUE" in str(e):
                return {"success": False, "message": "El username o email ya existe"}
            logger.error("Error en registro: %s", e)
            return {"success": False, "message": f"Error al registrar: {str(e)}"}

    def login(self, username: str, password: str) -> Dict:
        try:
            with Session(self.engine) as session:
                statement = select(User).where(User.username == username)
                user = session.exec(statement).first()

                if user and self._verify_password(password, user.password_hash):
                    user.last_login = datetime.now(timezone.utc)
                    session.add(user)
                    session.commit()
                    session.refresh(user)

                    token = self.create_access_token(user.id, user.username)
                    return {
                        "success": True,
                        "message": "Login exitoso",
                        "token": token,
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "created_at": user.created_at.isoformat() if user.created_at else None,
                        },
                    }
                return {"success": False, "message": "Usuario o contraseña incorrectos"}
        except Exception as e:
            logger.error("Error en login: %s", e)
            return {"success": False, "message": f"Error al iniciar sesión: {str(e)}"}

    # ── Perfil ─────────────────────────────────────────────────────

    def update_profile(self, user_id: int, profile_data: Dict) -> Dict:
        try:
            with Session(self.engine) as session:
                statement = select(StudentProfile).where(StudentProfile.user_id == user_id)
                profile = session.exec(statement).first()

                if not profile:
                    return {"success": False, "message": "Perfil no encontrado"}

                for key, value in profile_data.items():
                    if key in self.ALLOWED_PROFILE_FIELDS:
                        setattr(profile, key, value)

                session.add(profile)
                session.commit()
                return {"success": True, "message": "Perfil actualizado exitosamente"}
        except Exception as e:
            logger.error("Error actualizando perfil: %s", e)
            return {"success": False, "message": f"Error al actualizar: {str(e)}"}

    def get_profile(self, user_id: int) -> Optional[Dict]:
        try:
            with Session(self.engine) as session:
                statement = select(User).where(User.id == user_id)
                user = session.exec(statement).first()

                if user:
                    profile = user.profile
                    return {
                        "username": user.username,
                        "email": user.email,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                        "last_login": user.last_login.isoformat() if user.last_login else None,
                        "full_name": profile.full_name if profile else None,
                        "degree": profile.degree if profile else None,
                        "year": profile.year if profile else None,
                        "interests": profile.interests if profile else None,
                        "skills": profile.skills if profile else None,
                        "preferred_areas": profile.preferred_areas if profile else None,
                    }
            return None
        except Exception as e:
            logger.error("Error obteniendo perfil: %s", e)
            return None

    # ── Historial de Búsquedas ─────────────────────────────────────

    def add_search_history(self, user_id: int, query: str, search_type: str = "general"):
        try:
            with Session(self.engine) as session:
                history = SearchHistory(user_id=user_id, query=query, search_type=search_type)
                session.add(history)
                session.commit()
        except Exception as e:
            logger.error("Error guardando historial: %s", e)

    def get_search_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        try:
            with Session(self.engine) as session:
                statement = (
                    select(SearchHistory)
                    .where(SearchHistory.user_id == user_id)
                    .order_by(SearchHistory.timestamp.desc())
                    .limit(limit)
                )
                results = session.exec(statement).all()
                return [
                    {
                        "query": h.query,
                        "search_type": h.search_type,
                        "timestamp": h.timestamp.isoformat() if h.timestamp else None,
                    }
                    for h in results
                ]
        except Exception as e:
            logger.error("Error obteniendo historial: %s", e)
            return []

    def clear_search_history(self, user_id: int) -> Dict:
        try:
            with Session(self.engine) as session:
                statement = delete(SearchHistory).where(SearchHistory.user_id == user_id)
                session.exec(statement)
                session.commit()
                return {"success": True, "message": "Historial eliminado exitosamente"}
        except Exception as e:
            logger.error("Error eliminando historial: %s", e)
            return {"success": False, "message": f"Error al eliminar historial: {str(e)}"}