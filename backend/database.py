from datetime import datetime
from typing import Optional, Any, Dict, List

import enum # Ensure enum is imported
from sqlalchemy import create_engine, UniqueConstraint # Ensure UniqueConstraint is imported
from sqlmodel import Field, Session, SQLModel, Relationship
from pydantic import model_validator, computed_field, BaseModel

# --- Enum Definitions ---
class SaleStatusEnum(str, enum.Enum):
    PENDIENTE_PREPARACION = "pendiente_preparacion"
    ARMADO = "armado"
    EN_CAMINO = "en_camino"
    ENTREGADO = "entregado"
    COBRADO = "cobrado"
    CANCELADO = "cancelado"

class RedemptionRequestStatusEnum(str, enum.Enum):
    PENDIENTE_APROBACION = "pendiente_aprobacion"
    APROBADO_POR_ENTREGAR = "aprobado_por_entregar"
    ENTREGADO = "entregado"
    RECHAZADO = "rechazado"
    CANCELADO_POR_CLIENTE = "cancelado_por_cliente"
# --- End of Enum Definitions ---

DATABASE_URL = "sqlite:///./showroom_natura.db"
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# --- User Models ---
class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    is_seller: bool = Field(default=False)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    client_profile: Optional["ClientProfile"] = Relationship(back_populates="user")
    sales: List["Sale"] = Relationship(back_populates="user")
    wishlist_items: List["WishlistItem"] = Relationship(back_populates="user")
    cart: Optional["Cart"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int

class ClientProfileRead(SQLModel): # Forward reference
    id: int
    user_id: int
    nickname: Optional[str] = None
    whatsapp_number: Optional[str] = None
    gender: Optional[str] = None
    client_level: str = "Plata"
    profile_image_url: Optional[str] = None
    available_points: int # Added this as it's in the later full definition

class UserReadWithClientProfile(UserRead):
    client_profile: Optional[ClientProfileRead] = None

# --- ClientProfile Models ---
class ClientProfileBase(SQLModel):
    nickname: Optional[str] = None
    whatsapp_number: Optional[str] = Field(default=None, index=True)
    gender: Optional[str] = None
    client_level: str = Field(default="Plata")
    profile_image_url: Optional[str] = None

class ClientProfile(ClientProfileBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    available_points: int = Field(default=0, ge=0, nullable=False)
    user: User = Relationship(back_populates="client_profile")

class ClientProfileCreate(ClientProfileBase):
    user_id: int

class ClientProfileUpdate(SQLModel):
    nickname: Optional[str] = None
    whatsapp_number: Optional[str] = None
    gender: Optional[str] = None
    client_level: Optional[str] = None
    profile_image_url: Optional[str] = None

# Redefine ClientProfileRead for full structure (matches the one used in UserReadWithClientProfile)
class ClientProfileRead(ClientProfileBase): # Inherits from ClientProfileBase
    id: int
    user_id: int
    available_points: int

# --- Tag and ProductTag Link Models ---
class ProductTag(SQLModel, table=True):
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)
    product_id: Optional[int] = Field(default=None, foreign_key="product.id", primary_key=True)

class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=100, nullable=False)
    products: List["Product"] = Relationship(back_populates="tags", link_model=ProductTag)

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
    products: List["Product"] = Relationship(back_populates="category_obj")

class CategoryBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=512)

class CategoryCreate(CategoryBase):
    pass

class CategoryRead(CategoryBase):
    id: int

# Forward declaration for ProductRead to be used in CategoryReadWithProducts
class ProductRead(SQLModel):
    id: int
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = Field(default=None)
    price_revista: float = Field(default=0.0)
    price_showroom: Optional[float] = Field(default=None)
    price_feria: Optional[float] = Field(default=None)
    stock_actual: int = Field(default=0)
    stock_critico: Optional[int] = Field(default=0)
    tags: List[TagRead] = []
    category: Optional[CategoryRead] = None # CategoryRead is now defined above

class CategoryReadWithProducts(CategoryRead):
    products: List[ProductRead] = []

# --- Product Models ---
class ProductBase(SQLModel):
    name: str
    description: Optional[str] = None
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
    category_id: Optional[int] = Field(default=None, foreign_key="category.id", index=True, nullable=True)
    category_obj: Optional[Category] = Relationship(back_populates="products")
    catalog_entry_rel: Optional["CatalogEntry"] = Relationship(back_populates="product")

class ProductCreate(ProductBase):
    category_id: Optional[int] = Field(default=None)
    tag_names: Optional[List[str]] = Field(default_factory=list)
    @model_validator(mode='before')
    @classmethod
    def calculate_derived_prices(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        price_revista = values.get('price_revista', 0.0)
        if 'price_showroom' not in values or values.get('price_showroom') is None: values['price_showroom'] = price_revista * 0.80
        if 'price_feria' not in values or values.get('price_feria') is None: values['price_feria'] = price_revista * 0.65
        return values

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = Field(default=None)
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
            if 'price_showroom' not in values or values.get('price_showroom') is None: values['price_showroom'] = price_revista * 0.80
            if 'price_feria' not in values or values.get('price_feria') is None: values['price_feria'] = price_revista * 0.65
        return values

# Full definition of ProductRead (it was forward-declared earlier)
# No need to redefine if the forward declaration was complete enough.
# The forward declaration of ProductRead is now complete with 'category' field.

# Client Model (appears unused, but kept from original)
class Client(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

# Sale Models
class SaleBase(SQLModel):
    status: SaleStatusEnum = Field(default=SaleStatusEnum.PENDIENTE_PREPARACION)
    discount_amount: Optional[float] = Field(default=0.0)

# Forward declaration for SaleItemRead to be used in SaleRead
class SaleItemRead(SQLModel):
    id: int
    product_id: int # From SaleItemBase
    quantity: int # From SaleItemBase
    price_at_sale: Optional[float] # From SaleItemBase
    subtotal: float
    product: ProductRead

class SaleRead(SaleBase):
    id: int
    user_id: int
    sale_date: datetime
    updated_at: datetime
    items: List[SaleItemRead] = []
    total_amount: float
    points_earned: int
    user: Optional[UserRead] = None

class Sale(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    sale_date: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, sa_column_kwargs={"onupdate": datetime.utcnow})
    status: SaleStatusEnum = Field(default=SaleStatusEnum.PENDIENTE_PREPARACION, index=True, nullable=False)
    total_amount: float = Field(default=0.0)
    discount_amount: Optional[float] = Field(default=0.0)
    points_earned: Optional[int] = Field(default=0)
    user: User = Relationship(back_populates="sales")
    items: List["SaleItem"] = Relationship(back_populates="sale", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class SaleItemBase(SQLModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    price_at_sale: Optional[float] = Field(default=None, ge=0)

class SaleItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sale_id: int = Field(foreign_key="sale.id", index=True, nullable=False)
    product_id: int = Field(foreign_key="product.id", index=True, nullable=False)
    quantity: int = Field(gt=0, nullable=False)
    price_at_sale: float = Field(ge=0, nullable=False)
    subtotal: float = Field(default=0.0, ge=0, nullable=False)
    sale: Sale = Relationship(back_populates="items")
    product: Product = Relationship()

class SaleItemCreate(SaleItemBase):
    pass

# Full definition of SaleItemRead (it was forward-declared)
# class SaleItemRead(SaleItemBase): # No need to redefine if forward was sufficient
#     id: int
#     subtotal: float
#     product: ProductRead

class SaleCreate(SQLModel):
    user_id: Optional[int] = None
    status: Optional[SaleStatusEnum] = Field(default=SaleStatusEnum.PENDIENTE_PREPARACION)
    discount_amount: Optional[float] = Field(default=0.0, ge=0)
    items: List[SaleItemCreate]

class SaleUpdate(SaleBase):
    pass

# Full definition of SaleRead (it was forward-declared)
# class SaleRead(SaleBase):
#     id: int
#     user_id: int
#     sale_date: datetime
#     updated_at: datetime
#     items: List[SaleItemRead] = []
#     total_amount: float
#     points_earned: int
#     user: Optional[UserRead] = None

# --- User's Own Profile Update Schema ---
class MyProfileUpdate(SQLModel):
    nickname: Optional[str] = Field(default=None)
    whatsapp_number: Optional[str] = Field(default=None)
    gender: Optional[str] = Field(default=None)

# --- Wishlist Models ---
class WishlistItemBase(SQLModel):
    product_id: int = Field(foreign_key="product.id", index=True)

class WishlistItem(WishlistItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    added_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    user: User = Relationship(back_populates="wishlist_items")
    product: Product = Relationship(back_populates="wished_by_users")
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_user_product_wishlist"),)

class WishlistItemCreate(WishlistItemBase):
    pass

class WishlistItemRead(WishlistItemBase):
    id: int
    user_id: int
    added_at: datetime
    product: ProductRead

# --- Catalog Models ---
class CatalogEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", unique=True, index=True)
    is_visible_in_catalog: bool = Field(default=True)
    is_sold_out_in_catalog: bool = Field(default=False)
    promo_text: Optional[str] = Field(default=None, max_length=255)
    display_order: int = Field(default=0)
    catalog_price: Optional[float] = Field(default=None)
    catalog_image_url: Optional[str] = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    product: Product = Relationship(back_populates="catalog_entry_rel")

class CatalogEntryBase(SQLModel):
    product_id: int
    is_visible_in_catalog: bool = Field(default=True)
    is_sold_out_in_catalog: bool = Field(default=False)
    promo_text: Optional[str] = Field(default=None, max_length=255)
    display_order: int = Field(default=0)
    catalog_price: Optional[float] = Field(default=None)
    catalog_image_url: Optional[str] = Field(default=None, max_length=512)

class CatalogEntryCreate(CatalogEntryBase):
    pass

class CatalogEntryUpdate(SQLModel):
    is_visible_in_catalog: Optional[bool] = None
    is_sold_out_in_catalog: Optional[bool] = None
    promo_text: Optional[str] = Field(default=None, max_length=255)
    display_order: Optional[int] = None
    catalog_price: Optional[float] = None
    catalog_image_url: Optional[str] = Field(default=None, max_length=512)

class CatalogEntryApiResponse(BaseModel):
    id: int
    product_id: int
    is_visible_in_catalog: bool
    is_sold_out_in_catalog: bool
    promo_text: Optional[str] = None
    display_order: int
    created_at: datetime
    updated_at: datetime
    catalog_price: Optional[float] = None
    catalog_image_url: Optional[str] = None
    product: ProductRead
    effective_price: float
    effective_image_url: Optional[str]
    class Config: from_attributes = True

# --- Cart Models ---
class Cart(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, sa_column_kwargs={"onupdate": datetime.utcnow})
    items: List["CartItem"] = Relationship(back_populates="cart", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    user: User = Relationship(back_populates="cart")

class CartItemBase(SQLModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, gt=0)

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(SQLModel):
    quantity: int = Field(gt=0)

class CartItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cart_id: int = Field(foreign_key="cart.id", index=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    quantity: int = Field(default=1, gt=0)
    added_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    price_at_addition: Optional[float] = Field(default=None)
    cart: Cart = Relationship(back_populates="items")
    product: Product = Relationship()
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),)

class CartItemRead(CartItemBase):
    id: int
    price_at_addition: Optional[float] = None
    added_at: datetime
    product: ProductRead

class CartRead(SQLModel):
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
            if item.product:
                price_to_use = item.product.price_showroom if item.product.price_showroom is not None else item.product.price_revista
                if isinstance(price_to_use, (int, float)): total += item.quantity * price_to_use
        return round(total, 2)

# --- Site Configuration Model ---
class SiteConfiguration(SQLModel, table=True):
    id: Optional[int] = Field(default=1, primary_key=True, nullable=False)
    site_name: Optional[str] = Field(default="Showroom Natura OjitOs", max_length=255)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    logo_url: Optional[str] = Field(default=None, max_length=512)
    color_primary: Optional[str] = Field(default="#E83E8C", max_length=7)
    color_secondary: Optional[str] = Field(default="#FF7F00", max_length=7)
    color_accent: Optional[str] = Field(default="#4CAF50", max_length=7)
    social_instagram_url: Optional[str] = Field(default=None, max_length=512)
    social_tiktok_url: Optional[str] = Field(default=None, max_length=512)
    social_whatsapp_url: Optional[str] = Field(default=None, max_length=512)
    online_fair_url: Optional[str] = Field(default=None, max_length=512)
    showroom_address: Optional[str] = Field(default=None, max_length=1024)
    system_param_points_per_currency_unit: Optional[float] = Field(default=0.1, ge=0)
    system_param_default_showroom_discount_percentage: Optional[int] = Field(default=20, ge=0, le=100)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow}, nullable=False)

class SiteConfigurationRead(SQLModel):
    site_name: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    logo_url: Optional[str]
    color_primary: str
    color_secondary: str
    color_accent: str
    social_instagram_url: Optional[str]
    social_tiktok_url: Optional[str]
    social_whatsapp_url: Optional[str]
    online_fair_url: Optional[str]
    showroom_address: Optional[str]
    system_param_points_per_currency_unit: float
    system_param_default_showroom_discount_percentage: int
    updated_at: datetime

class SiteConfigurationUpdate(SQLModel):
    site_name: Optional[str] = Field(default=None, max_length=255)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    color_primary: Optional[str] = Field(default=None, max_length=7)
    color_secondary: Optional[str] = Field(default=None, max_length=7)
    color_accent: Optional[str] = Field(default=None, max_length=7)
    social_instagram_url: Optional[str] = Field(default=None, max_length=512)
    social_tiktok_url: Optional[str] = Field(default=None, max_length=512)
    social_whatsapp_url: Optional[str] = Field(default=None, max_length=512)
    online_fair_url: Optional[str] = Field(default=None, max_length=512)
    showroom_address: Optional[str] = Field(default=None, max_length=1024)
    system_param_points_per_currency_unit: Optional[float] = Field(default=None, ge=0)
    system_param_default_showroom_discount_percentage: Optional[int] = Field(default=None, ge=0, le=100)

# --- Gift Item Model ---
# Forward declaration for GiftItemRead to be used in RedemptionRequestRead
class GiftItemRead(SQLModel):
    id: int
    product_id: int
    points_required: int
    stock_available_for_redeem: int
    is_active_as_gift: bool
    created_at: datetime
    updated_at: datetime
    product: ProductRead

class GiftItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", unique=True, index=True, nullable=False)
    points_required: int = Field(gt=0, nullable=False)
    stock_available_for_redeem: int = Field(default=0, ge=0, nullable=False)
    is_active_as_gift: bool = Field(default=True, index=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow}, nullable=False)
    product: Product = Relationship()

class GiftItemBase(SQLModel):
    product_id: int = Field(gt=0)
    points_required: int = Field(gt=0)
    stock_available_for_redeem: int = Field(default=0, ge=0)
    is_active_as_gift: bool = Field(default=True)

class GiftItemCreate(GiftItemBase):
    pass

class GiftItemUpdate(SQLModel):
    points_required: Optional[int] = Field(default=None, gt=0)
    stock_available_for_redeem: Optional[int] = Field(default=None, ge=0)
    is_active_as_gift: Optional[bool] = None

# Full definition of GiftItemRead (it was forward-declared)
# class GiftItemRead(GiftItemBase): # No need to redefine if forward was sufficient
#     id: int
#     created_at: datetime
#     updated_at: datetime
#     product: ProductRead

# --- Redemption Request Model ---
class RedemptionRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    gift_item_id: int = Field(foreign_key="giftitem.id", index=True, nullable=False)
    points_at_request: int = Field(gt=0, nullable=False)
    product_details_at_request: Optional[str] = Field(default=None, max_length=1024)
    status: RedemptionRequestStatusEnum = Field(default=RedemptionRequestStatusEnum.PENDIENTE_APROBACION, index=True, nullable=False)
    requested_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow}, nullable=False)
    admin_notes: Optional[str] = Field(default=None, max_length=512)
    user: User = Relationship()
    gift_item: GiftItem = Relationship()

class RedemptionRequestBase(SQLModel):
    gift_item_id: int = Field(gt=0)

class RedemptionRequestCreate(RedemptionRequestBase):
    pass

class RedemptionRequestUpdateAdmin(SQLModel):
    status: Optional[RedemptionRequestStatusEnum] = None
    admin_notes: Optional[str] = Field(default=None, max_length=512)

class RedemptionActionPayload(SQLModel):
    admin_notes: Optional[str] = Field(default=None, max_length=512)

class RedemptionRequestRead(SQLModel):
    id: int
    user_id: int
    gift_item_id: int
    points_at_request: int
    product_details_at_request: Optional[str]
    status: RedemptionRequestStatusEnum
    requested_at: datetime
    updated_at: datetime
    admin_notes: Optional[str]
    gift_item: GiftItemRead # GiftItemRead is now fully defined or forward-declared
    user: Optional[UserRead] = None
