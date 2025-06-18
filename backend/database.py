from datetime import datetime
from typing import Optional, Any, Dict

from sqlalchemy import create_engine
from sqlmodel import Field, Session, SQLModel
from pydantic import model_validator


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


# --- Product Models ---

class ProductBase(SQLModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, index=True)
    tags: Optional[str] = Field(default=None) # Could be a JSON string or handled differently
    image_url: Optional[str] = Field(default=None)

    price_revista: float = Field(default=0.0)
    price_showroom: Optional[float] = Field(default=None)
    price_feria: Optional[float] = Field(default=None)

    stock_actual: int = Field(default=0)
    stock_critico: Optional[int] = Field(default=0)

class Product(ProductBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Inherits all fields from ProductBase
    # price_showroom and price_feria will store the calculated values if provided,
    # or the result of calculations if not. They remain Optional in the DB.

class ProductCreate(ProductBase):
    @model_validator(mode='before')
    @classmethod
    def calculate_derived_prices(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        price_revista = values.get('price_revista', 0.0)

        if 'price_showroom' not in values or values.get('price_showroom') is None:
            values['price_showroom'] = price_revista * 0.80

        if 'price_feria' not in values or values.get('price_feria') is None:
            values['price_feria'] = price_revista * 0.65

        return values

class ProductUpdate(SQLModel): # All fields should be optional for updates
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, index=True) # Index might not be updatable this way, but field is optional
    tags: Optional[str] = None
    image_url: Optional[str] = None

    price_revista: Optional[float] = None
    price_showroom: Optional[float] = None
    price_feria: Optional[float] = None

    stock_actual: Optional[int] = None
    stock_critico: Optional[int] = None

    @model_validator(mode='before')
    @classmethod
    def calculate_derived_prices_on_update(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if 'price_revista' in values and values['price_revista'] is not None:
            price_revista = values['price_revista']
            # Only calculate if not explicitly provided in the update payload
            if 'price_showroom' not in values or values.get('price_showroom') is None:
                values['price_showroom'] = price_revista * 0.80
            if 'price_feria' not in values or values.get('price_feria') is None:
                values['price_feria'] = price_revista * 0.65
        # If price_revista is not being updated, but showroom/feria prices are,
        # we let them be updated to their explicit values.
        # If price_revista is not updated, and showroom/feria are also not updated,
        # then existing values in DB remain (or they are set to None if that's passed).
        return values

class ProductRead(ProductBase):
    id: int
    # This model ensures that when reading data, it conforms to ProductBase structure + id.
    # The calculated prices should be populated by the create/update logic before saving.

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
