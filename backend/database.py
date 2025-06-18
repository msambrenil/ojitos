from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlmodel import Field, Session, SQLModel


DATABASE_URL = "sqlite:///./showroom_natura.db"

engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# User Models
class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    full_name: Optional[str] = None
    disabled: bool = False

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str

class UserCreate(UserBase):
    password: str


# Product Model
class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0


# Client Model
class Client(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


# Sale Model
class Sale(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")
    sale_date: datetime = Field(default_factory=datetime.utcnow)
    total_amount: float
    status: str  # e.g., "Por Armar", "A Entregar", "Entregada", "Cobrada"

# Note: To establish relationships like Sale referencing Client,
# you might need to add Relationship attributes from SQLModel later on if you build out ORM features.
# For now, client_id: int = Field(foreign_key="client.id") sets up the foreign key constraint at DB level.
