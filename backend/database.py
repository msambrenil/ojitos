from datetime import datetime
from typing import Optional, Any, Dict, List

from sqlalchemy import create_engine, UniqueConstraint
from sqlmodel import Field, Session, SQLModel, Relationship
from pydantic import model_validator, computed_field # Added computed_field


DATABASE_URL = "sqlite:///./showroom_natura.db"

engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# User Models
class UserBase(SQLModel):
    email: str = Field(unique=True, index=True) # Changed username to email as primary identifier
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    # Removed: username, disabled

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str

    client_profile: Optional["ClientProfile"] = Relationship(back_populates="user")
    sales: List["Sale"] = Relationship(back_populates="user_as_client")
    wishlist_items: List["WishlistItem"] = Relationship(back_populates="user")
    cart: Optional["Cart"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}) # Added cart relationship

class UserCreate(UserBase): # For user creation, password is required
    password: str

class UserRead(UserBase): # Basic User info for reading
    id: int

# Forward reference for ClientProfileRead used in UserReadWithClientProfile
class ClientProfileRead(SQLModel): # Define structure first
    id: int
    user_id: int
    nickname: Optional[str] = None
    whatsapp_number: Optional[str] = None
    gender: Optional[str] = None
    client_level: str = "Plata"
    profile_image_url: Optional[str] = None

class UserReadWithClientProfile(UserRead): # Richer user representation
    client_profile: Optional[ClientProfileRead] = None


# --- ClientProfile Models ---
class ClientProfileBase(SQLModel):
    nickname: Optional[str] = None
    whatsapp_number: Optional[str] = Field(default=None, index=True)
    gender: Optional[str] = None  # Consider using an Enum later
    client_level: str = Field(default="Plata") # Default to "Plata"
    profile_image_url: Optional[str] = None

class ClientProfile(ClientProfileBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True) # Ensures one-to-one

    user: User = Relationship(back_populates="client_profile")

class ClientProfileCreate(ClientProfileBase):
    user_id: int # Required when creating a profile

class ClientProfileUpdate(SQLModel): # All fields optional for PATCH-like behavior
    nickname: Optional[str] = None
    whatsapp_number: Optional[str] = None
    gender: Optional[str] = None
    client_level: Optional[str] = None
    profile_image_url: Optional[str] = None

# Re-define ClientProfileRead here if it needs to inherit from ClientProfileBase
# to pick up fields correctly. The forward reference above was just for UserReadWithClientProfile.
class ClientProfileRead(ClientProfileBase): # Now inherits from ClientProfileBase
    id: int
    user_id: int
    # nickname, whatsapp_number, etc. are inherited from ClientProfileBase


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
    wished_by_users: List["WishlistItem"] = Relationship(back_populates="product") # Added wished_by_users
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


# Sale Model (Updated)
class SaleBase(SQLModel):
    sale_date: datetime = Field(default_factory=datetime.utcnow)
    total_amount: float
    status: str  # e.g., "Por Armar", "A Entregar", "Entregada", "Cobrada"

class Sale(SaleBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True) # Renamed from client_id, linked to User, indexed

    # Relationship to User (as the client who made the purchase)
    user_as_client: Optional[User] = Relationship(back_populates="sales")
    # If you also need to track which user (e.g. salesperson) registered the sale,
    # you would add another field like `registered_by_user_id` and another relationship.

class SaleRead(SaleBase):
    id: int
    user_id: int # Changed from client_id to match Sale model

# Note: The existing Client model might be for something else, or might be redundant if users are always clients.
# For now, focusing on Sale being linked to User via user_id.


# --- User's Own Profile Update Schema ---
class MyProfileUpdate(SQLModel):
    nickname: Optional[str] = Field(default=None)
    whatsapp_number: Optional[str] = Field(default=None) # Consider adding validation for phone numbers later
    gender: Optional[str] = Field(default=None)
    # Excludes client_level (managed by admin) and profile_image_url (managed by separate endpoint)


# --- Wishlist Models ---
class WishlistItemBase(SQLModel):
    product_id: int = Field(foreign_key="product.id", index=True) # product_id is essential

class WishlistItem(WishlistItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    added_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    user: User = Relationship(back_populates="wishlist_items")
    product: Product = Relationship(back_populates="wished_by_users")

    # Unique constraint for user_id and product_id
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_user_product_wishlist"),)

class WishlistItemCreate(WishlistItemBase):
    pass # product_id is inherited, user_id will be from context

class WishlistItemRead(WishlistItemBase):
    id: int
    user_id: int
    added_at: datetime
    product: ProductRead # Embed Product details


# --- Cart Models ---
class Cart(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True) # One cart per user
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, sa_column_kwargs={"onupdate": datetime.utcnow})

    # Relationships
    items: List["CartItem"] = Relationship(back_populates="cart", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    user: "User" = Relationship(back_populates="cart")


class CartItemBase(SQLModel):
    product_id: int = Field(gt=0) # Ensure product_id is positive
    quantity: int = Field(default=1, gt=0)


class CartItemCreate(CartItemBase):
    pass # Inherits fields from CartItemBase


class CartItemUpdate(SQLModel):
    quantity: int = Field(gt=0) # Quantity must be positive


class CartItem(SQLModel, table=True): # Define table model after base and create/update schemas
    id: Optional[int] = Field(default=None, primary_key=True)
    cart_id: int = Field(foreign_key="cart.id", index=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    quantity: int = Field(default=1, gt=0)
    added_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    price_at_addition: Optional[float] = Field(default=None) # Price when product was added

    # Relationships
    cart: "Cart" = Relationship(back_populates="items")
    product: "Product" = Relationship() # Uni-directional for now

    # Unique constraint for cart_id and product_id
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),)


class CartItemRead(CartItemBase): # For API responses
    id: int
    # product_id and quantity inherited from CartItemBase
    price_at_addition: Optional[float] = None
    added_at: datetime # Added from CartItem model
    product: "ProductRead"


class CartRead(SQLModel): # For API response for the whole cart
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    items: List[CartItemRead] = []

    @computed_field
    @property
    def total_cart_price(self) -> float:
        total = 0.0
        for item in self.items:
            # Ensure product and its price_revista are available
            # price_revista is not optional on ProductBase, so it should exist.
            if item.product and isinstance(item.product.price_revista, (int, float)):
                total += item.quantity * item.product.price_revista
        return round(total, 2)
