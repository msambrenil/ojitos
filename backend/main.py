from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional # Ensure Optional is imported if not already

# Assuming models are in database.py. Adjust if you created a separate models.py
from .database import create_db_and_tables, engine
from .database import User, UserCreate # User will be used as UserRead effectively for now
# SQLModel Session will be needed later for actual DB operations
# from sqlmodel import Session


app = FastAPI()

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


# --- Placeholder Authentication Routes ---

# OAuth2 scheme (not strictly needed for placeholders but good for structure)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # In a real app, you'd verify form_data.username and form_data.password
    # and then create a real JWT token.
    # For now, this is a placeholder.
    # Note: python-multipart needs to be installed for form data.
    return {"access_token": form_data.username + "_fake_token", "token_type": "bearer"}

@app.post("/users/", response_model=User) # Using User as UserRead for now
async def create_user(user: UserCreate):
    # In a real app, you would:
    # 1. Hash user.password
    # 2. Create a User instance with the hashed password
    # 3. Add it to the database session and commit
    # 4. Return the created user (without the hashed_password for security, or use a UserRead model)

    # Placeholder implementation:
    # Creating a User instance to match the response_model, but not saving it.
    # The hashed_password would normally be generated, not taken directly.
    # For this placeholder, we'll just make one up.
    dummy_hashed_password = user.password + "_hashed"

    # Create a dictionary that matches the fields of the User model for the response.
    # This avoids trying to instantiate User directly with 'password' field from UserCreate.
    user_data_for_response = user.model_dump()
    user_data_for_response.pop("password", None) # Remove password if it's part of UserCreate but not UserBase/User

    return User(
        id=99, # Dummy ID
        hashed_password=dummy_hashed_password,
        **user_data_for_response # Spread UserBase fields
    )

# Example of a protected route (placeholder)
@app.get("/users/me", response_model=User) # Using User as UserRead
async def read_users_me(token: str = Depends(oauth2_scheme)):
    # In a real app, you'd decode the token to get the current user.
    # For now, return a dummy user.
    return User(
        id=1,
        username="currentuser",
        email="current@example.com",
        full_name="Current User",
        disabled=False,
        hashed_password="fake_hashed_password" # This wouldn't normally be returned
    )
