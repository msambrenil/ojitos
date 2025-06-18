import os
import shutil
import uuid
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, select

# Assuming models are in database.py. Adjust if you created a separate models.py
from .database import (
    create_db_and_tables,
    engine,
    User,
    UserCreate,
    Product,
    ProductCreate,
    ProductRead,
    ProductUpdate
)


app = FastAPI()

# --- Static Files Setup ---
os.makedirs("static/product_images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Dependency for DB Session ---
def get_session():
    with Session(engine) as session:
        yield session

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Pydantic model for card data (remains from previous step)
class CardData(BaseModel):
    title: str
    value: str

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

# Endpoints for dashboard cards (remain from previous step)
@app.get("/api/dashboard/ventas-entregadas", response_model=CardData)
async def get_ventas_entregadas():
    return CardData(title="Ventas Entregadas", value="125")

@app.get("/api/dashboard/a-entregar", response_model=CardData)
async def get_a_entregar():
    return CardData(title="A Entregar", value="30")

@app.get("/api/dashboard/por-armar", response_model=CardData)
async def get_por_armar():
    return CardData(title="Por Armar", value="15")

@app.get("/api/dashboard/cobradas", response_model=CardData)
async def get_cobradas():
    return CardData(title="Cobradas", value="S/. 10,500")

@app.get("/api/dashboard/a-cobrar", response_model=CardData)
async def get_a_cobrar():
    return CardData(title="A Cobrar", value="S/. 2,300")




# --- Products Router ---
products_router = APIRouter(prefix="/api/products", tags=["Products"])

@products_router.post("/", response_model=ProductRead)
async def create_product_endpoint(
    product_in: ProductCreate = Depends(),
    image: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session)
):
    image_url_for_db = None
    if image:
        # Ensure the filename is somewhat safe and unique
        filename = f"{uuid.uuid4()}_{image.filename.replace('..', '')}"
        file_path = f"static/product_images/{filename}"

        # Basic check for common web image types
        if image.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            raise HTTPException(status_code=400, detail="Invalid image file type. Please upload jpeg, png, gif, or webp.")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url_for_db = f"/{file_path}" # Store path relative to static mount

    # ProductCreate model already calculated derived prices if needed
    db_product_data = product_in.model_dump()
    db_product_data["image_url"] = image_url_for_db

    # Validate data with Product model (table model) before saving to DB
    db_product = Product.model_validate(db_product_data)

    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product

@products_router.get("/", response_model=List[ProductRead])
def read_products_endpoint(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    session: Session = Depends(get_session)
):
    query = select(Product)
    if category:
        query = query.where(Product.category == category)
    query = query.offset(skip).limit(limit)
    products = session.exec(query).all()
    return products

@products_router.get("/{product_id}", response_model=ProductRead)
def read_product_endpoint(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@products_router.put("/{product_id}", response_model=ProductRead)
async def update_product_endpoint(
    product_id: int,
    product_update_data: ProductUpdate = Depends(), # Use ProductUpdate for input
    image: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session)
):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get data from ProductUpdate model, excluding unset values
    update_data = product_update_data.model_dump(exclude_unset=True)

    if image:
        # Basic check for common web image types
        if image.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            raise HTTPException(status_code=400, detail="Invalid image file type. Please upload jpeg, png, gif, or webp.")

        # Delete old image if it exists and is different
        if db_product.image_url:
            old_image_path = db_product.image_url.lstrip('/')
            if os.path.exists(old_image_path):
                try:
                    os.remove(old_image_path)
                except OSError as e:
                    print(f"Error deleting old image {old_image_path}: {e}") # Log error

        # Save new image
        filename = f"{uuid.uuid4()}_{image.filename.replace('..', '')}"
        file_path = f"static/product_images/{filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        update_data["image_url"] = f"/{file_path}"
    elif "image_url" in update_data and update_data["image_url"] is None:
        # If image_url is explicitly set to null, delete the existing image
        if db_product.image_url:
            old_image_path = db_product.image_url.lstrip('/')
            if os.path.exists(old_image_path):
                try:
                    os.remove(old_image_path)
                except OSError as e:
                    print(f"Error deleting image {old_image_path}: {e}") # Log error
        update_data["image_url"] = None


    # Apply updates to the database product object
    for key, value in update_data.items():
        setattr(db_product, key, value)

    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product

@products_router.delete("/{product_id}", response_model=dict)
def delete_product_endpoint(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Delete image file if it exists
    if product.image_url:
        image_file_path = product.image_url.lstrip('/') # Remove leading '/'
        if os.path.exists(image_file_path):
            try:
                os.remove(image_file_path)
            except OSError as e:
                # Log the error, but proceed with deleting the DB record
                print(f"Error deleting image file {image_file_path}: {e}")

    session.delete(product)
    session.commit()
    return {"message": "Product deleted successfully"}

app.include_router(products_router)


# --- Placeholder Authentication Routes (Kept from previous steps) ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    return {"access_token": form_data.username + "_fake_token", "token_type": "bearer"}

@app.post("/users/", response_model=User)
async def create_user(user: UserCreate):
    dummy_hashed_password = user.password + "_hashed"
    user_data_for_response = user.model_dump()
    user_data_for_response.pop("password", None)
    return User(
        id=99,
        hashed_password=dummy_hashed_password,
        **user_data_for_response
    )

@app.get("/users/me", response_model=User)
async def read_users_me(token: str = Depends(oauth2_scheme)):
    return User(
        id=1,
        username="currentuser",
        email="current@example.com",
        full_name="Current User",
        disabled=False,
        hashed_password="fake_hashed_password"
    )
