from datetime import datetime
from typing import Optional, Any, Dict, List

import enum # Added enum import
from sqlalchemy import create_engine, UniqueConstraint
from sqlmodel import Field, Session, SQLModel, Relationship
from pydantic import model_validator, computed_field, BaseModel # Added BaseModel


DATABASE_URL = "sqlite:///./showroom_natura.db"

engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# User Models
class UserBase(SQLModel):
    email: str = Field(unique=True, index=True) # Changed username to email as primary identifier
    full_name: Optional[str] = None
    is_active: bool = Field(default=True) # Default from previous updates
    is_superuser: bool = Field(default=False) # Default from previous updates
    is_seller: bool = Field(default=False)
    # Removed: username, disabled

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str

    client_profile: Optional["ClientProfile"] = Relationship(back_populates="user")
    sales: List["Sale"] = Relationship(back_populates="user") # Standardized back_populates
    wishlist_items: List["WishlistItem"] = Relationship(back_populates="user")
    cart: Optional["Cart"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

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


# --- Tag and ProductTag Link Models ---
class ProductTag(SQLModel, table=True):
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)
    product_id: Optional[int] = Field(default=None, foreign_key="product.id", primary_key=True)

class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=100, nullable=False)

    products: List["Product"] = Relationship(back_populates="tags", link_model=ProductTag)

# Pydantic Schemas for Tag
class TagBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)

class TagCreate(TagBase):
    pass

class TagRead(TagBase):
    id: int


# --- Category Model ---
class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=100, nullable=False)
    description: Optional[str] = Field(default=None, max_length=512)

    # Relationship to Product model
    products: List["Product"] = Relationship(back_populates="category_obj")

# Pydantic Schemas for Category
class CategoryBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=512)

class CategoryCreate(CategoryBase):
    pass

class CategoryRead(CategoryBase):
    id: int

class CategoryReadWithProducts(CategoryRead):
    products: List["ProductRead"] = []


# --- Product Models ---

class ProductBase(SQLModel): # Fields common to ProductRead, does not include category_id
    name: str
    description: Optional[str] = None
    # category: Optional[str] = Field(default=None, index=True) # Removed old string category field
    # tags: Optional[str] = Field(default=None) # Removed old string tags field
    image_url: Optional[str] = Field(default=None)

    price_revista: float = Field(default=0.0)
    price_showroom: Optional[float] = Field(default=None)
    price_feria: Optional[float] = Field(default=None)

    stock_actual: int = Field(default=0)
    stock_critico: Optional[int] = Field(default=0)

class Product(ProductBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    wished_by_users: List["WishlistItem"] = Relationship(back_populates="product")

    tags: List["Tag"] = Relationship(back_populates="products", link_model=ProductTag)

    # Category relationship
    category_id: Optional[int] = Field(default=None, foreign_key="category.id", index=True, nullable=True)
    category_obj: Optional["Category"] = Relationship(back_populates="products")
    # Inherits all fields from ProductBase
    # price_showroom and price_feria will store the calculated values if provided,
    # or the result of calculations if not. They remain Optional in the DB.
    catalog_entry_rel: Optional["CatalogEntry"] = Relationship(back_populates="product")


class ProductCreate(ProductBase): # Inherits name, desc, prices, stock etc. from ProductBase
    category_id: Optional[int] = Field(default=None) # For linking to a category
    tag_names: Optional[List[str]] = Field(default_factory=list)

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
    category_id: Optional[int] = Field(default=None) # Allow updating or unsetting category
    tag_names: Optional[List[str]] = None
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

class ProductRead(ProductBase): # ProductBase no longer has string category or tags
    id: int
    tags: List[TagRead] = []
    category: Optional["CategoryRead"] = None # Populated from product.category_obj
    # This model ensures that when reading data, it conforms to ProductBase structure + id.
    # The calculated prices should be populated by the create/update logic before saving.

# Client Model
class Client(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


# Sale Models (Updated Structure)

# Minimal SaleBase for Pydantic schemas (like SaleUpdate, part of SaleRead)
class SaleBase(SQLModel):
    status: SaleStatusEnum = Field(default=SaleStatusEnum.PENDIENTE_PREPARACION)
    discount_amount: Optional[float] = Field(default=0.0)
    # Note: total_amount and points_earned are calculated/set by logic, not direct base input for update.

class Sale(SQLModel, table=True): # Table Model
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    sale_date: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, sa_column_kwargs={"onupdate": datetime.utcnow})

    status: SaleStatusEnum = Field(default=SaleStatusEnum.PENDIENTE_PREPARACION, index=True, nullable=False)

    total_amount: float = Field(default=0.0) # Calculated and stored by application logic
    discount_amount: Optional[float] = Field(default=0.0)
    points_earned: Optional[int] = Field(default=0) # Calculated and stored by application logic

    # Relationships
    user: User = Relationship(back_populates="sales") # Standardized relationship
    items: List["SaleItem"] = Relationship(back_populates="sale", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


# SaleRead will be defined after SaleItem, SaleItemRead are defined, as it might include items.
# For now, let's update the old SaleRead to match the new SaleBase structure,
# but it will be expanded later.
class SaleRead(SaleBase): # Temporary update, will be expanded
    id: int
    user_id: int
    sale_date: datetime
    updated_at: datetime
    total_amount: float
    points_earned: Optional[int]


# --- SaleItem Models ---
class SaleItemBase(SQLModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    price_at_sale: Optional[float] = Field(default=None, ge=0) # Optional at creation, to be resolved by logic

class SaleItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sale_id: int = Field(foreign_key="sale.id", index=True, nullable=False)
    product_id: int = Field(foreign_key="product.id", index=True, nullable=False)
    quantity: int = Field(gt=0, nullable=False)

    price_at_sale: float = Field(ge=0, nullable=False) # Actual price used, required in DB
    subtotal: float = Field(default=0.0, ge=0, nullable=False) # Calculated: quantity * price_at_sale

    # Relationships
    sale: "Sale" = Relationship(back_populates="items")
    product: "Product" = Relationship() # Uni-directional to Product is fine


class SaleItemCreate(SaleItemBase):
    pass # Inherits product_id, quantity, price_at_sale (optional)

class SaleItemRead(SaleItemBase):
    id: int
    subtotal: float # This will be populated by app logic before response
    product: "ProductRead"


# Schemas for Sale operations
class SaleCreate(SQLModel):
    user_id: Optional[int] = None # Admin can set this; for self-service, taken from current_user
    status: Optional[SaleStatusEnum] = Field(default=SaleStatusEnum.PENDIENTE_PREPARACION)
    discount_amount: Optional[float] = Field(default=0.0, ge=0)
    items: List[SaleItemCreate]


class SaleUpdate(SaleBase): # Inherits status, discount_amount from SaleBase
    pass # Add other specific fields an admin might update on Sale itself if any


# Redefine SaleRead to include SaleItemRead and UserRead
class SaleRead(SaleBase): # Inherits status, discount_amount
    id: int
    user_id: int
    sale_date: datetime
    updated_at: datetime
    items: List[SaleItemRead] = []

    total_amount: float
    points_earned: int

    user: Optional[UserRead] = None # Embed basic user info


# Note: The existing Client model might be for something else.

# --- Sale Status Enum ---
class SaleStatusEnum(str, enum.Enum):
    PENDIENTE_PREPARACION = "pendiente_preparacion" # Default initial state
    ARMADO = "armado"                             # Order is assembled
    EN_CAMINO = "en_camino"                       # Order is out for delivery
    ENTREGADO = "entregado"                       # Order has been delivered
    COBRADO = "cobrado"                           # Payment has been confirmed
    CANCELADO = "cancelado"                       # Order was cancelled
    # PENDIENTE_PAGO = "pendiente_pago"
    # PAGO_RECHAZADO = "pago_rechazado"
    # DEVUELTO = "devuelto"


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

class CatalogEntryApiResponse(BaseModel):
    # Fields from CatalogEntry table model / CatalogEntryBase
    id: int
    product_id: int
    is_visible_in_catalog: bool
    is_sold_out_in_catalog: bool
    promo_text: Optional[str] = None
    display_order: int
    created_at: datetime
    updated_at: datetime

    # Fields that might be overridden (actual values from CatalogEntry ORM object)
    catalog_price: Optional[float] = None
    catalog_image_url: Optional[str] = None

    # Nested product details
    product: ProductRead

    # Effective fields to be calculated and populated by endpoint logic
    effective_price: float
    effective_image_url: Optional[str]

    class Config:
        from_attributes = True # For Pydantic V2, to allow creating from ORM objects


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


# --- Site Configuration Model ---
class SiteConfiguration(SQLModel, table=True):
    # Using a fixed ID to enforce a singleton pattern (only one row in this table)
    # The application logic will always try to get/update the row with id=1.
    id: Optional[int] = Field(default=1, primary_key=True, nullable=False)

    site_name: Optional[str] = Field(default="Showroom Natura OjitOs", max_length=255)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    logo_url: Optional[str] = Field(default=None, max_length=512) # URL or path to logo

    # Brand Colors (stored as hex, e.g., "#RRGGBB")
    color_primary: Optional[str] = Field(default="#E83E8C", max_length=7) # Example: Natura Pink
    color_secondary: Optional[str] = Field(default="#FF7F00", max_length=7) # Example: Natura Orange
    color_accent: Optional[str] = Field(default="#4CAF50", max_length=7)  # Example: Natura Green

    # Social Media Links
    social_instagram_url: Optional[str] = Field(default=None, max_length=512)
    social_tiktok_url: Optional[str] = Field(default=None, max_length=512)
    social_whatsapp_url: Optional[str] = Field(default=None, max_length=512) # e.g., wa.me link
    online_fair_url: Optional[str] = Field(default=None, max_length=512)

    # Physical Address
    showroom_address: Optional[str] = Field(default=None, max_length=1024) # Free text or structured JSON string

    # System Parameters
    system_param_points_per_currency_unit: Optional[float] = Field(default=0.1, ge=0) # e.g., 0.1 points per S/.1
    system_param_default_showroom_discount_percentage: Optional[int] = Field(default=20, ge=0, le=100)

    # Timestamps
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
        nullable=False
    )


# --- Site Configuration Pydantic Schemas ---
class SiteConfigurationRead(SQLModel):
    # Based on SiteConfiguration table model, id is not usually sent to client for singleton config
    site_name: str # Has default in table, so expected in read
    contact_email: Optional[str]
    contact_phone: Optional[str]
    logo_url: Optional[str] # URL for the logo, managed by separate endpoint
    color_primary: str # Has default
    color_secondary: str # Has default
    color_accent: str # Has default
    social_instagram_url: Optional[str]
    social_tiktok_url: Optional[str]
    social_whatsapp_url: Optional[str]
    online_fair_url: Optional[str]
    showroom_address: Optional[str]
    system_param_points_per_currency_unit: float # Has default
    system_param_default_showroom_discount_percentage: int # Has default
    updated_at: datetime

class SiteConfigurationUpdate(SQLModel):
    site_name: Optional[str] = Field(default=None, max_length=255)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    # logo_url is managed by a separate endpoint, not included here.
    color_primary: Optional[str] = Field(default=None, max_length=7) # Hex color validation can be added with custom validator if needed
    color_secondary: Optional[str] = Field(default=None, max_length=7)
    color_accent: Optional[str] = Field(default=None, max_length=7)
    social_instagram_url: Optional[str] = Field(default=None, max_length=512)
    social_tiktok_url: Optional[str] = Field(default=None, max_length=512)
    social_whatsapp_url: Optional[str] = Field(default=None, max_length=512)
    online_fair_url: Optional[str] = Field(default=None, max_length=512)
    showroom_address: Optional[str] = Field(default=None, max_length=1024)
    system_param_points_per_currency_unit: Optional[float] = Field(default=None, ge=0)
    system_param_default_showroom_discount_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    # id and updated_at are not directly updatable by client.
