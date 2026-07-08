# main.py
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks 
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware 

from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from typing import List
import time 

import models
import schemas
import auth
from database import engine, get_db, SessionLocal

def send_welcome_email(username: str):
    print(f"\n[FON REJIM] >>> '{username}' foydalanuvchisi uchun xush kelibsiz xati tayyorlanyapti...")
    time.sleep(5) 
    print(f"[FON REJIM] >>> '{username}' uchun xat muvaffaqiyatli yuborildi! ✅\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        superadmin = db.query(models.DbUser).filter(models.DbUser.role == "superadmin").first()
        if not superadmin:
            hashed_pwd = auth.get_password_hash("Superadmin123!") # Validatorga mos, raqam va katta harfli parol
            new_superadmin = models.DbUser(
                username="superadmin",
                hashed_password=hashed_pwd,
                role="superadmin"
            )
            db.add(new_superadmin)
            db.commit()
            print(">>> INFO: Superadmin foydalanuvchisi muvaffaqiyatli yaratildi! (username: superadmin, parol: Superadmin123!)")
        else:
            print(">>> INFO: Superadmin allaqachon bazada mavjud.")
    except Exception as e:
        print(f">>> ERROR: Seed jarayonida xatolik yuz berdi: {e}")
    finally:
        db.close()
    yield

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:3000",      # React (CRA) default porti
    "http://localhost:5173",      # Vite (React/Vue) default porti
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    # Ertaga loyihani serverga qo'yganda, frontend domenini ham shu yerga qo'shasiz, masalan:
    # "https://myfrontendapp.uz"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Ruxsat berilgan domenlar ro'yxati
    allow_credentials=True,           # Cookie va avtorizatsiya sarlavhalarini yuborishga ruxsat
    allow_methods=["*"],              # Barcha metodlarga ruxsat (GET, POST, PUT, DELETE va h.k.)
    allow_headers=["*"],              # Barcha sarlavhalarga (Headers) ruxsat
)
# 1. Ro'yxatdan o'tish (Register + Background Task)
@app.post("/register", response_model=schemas.UserResponse)
def register(
    user: schemas.UserCreate, 
    background_tasks: BackgroundTasks, # <-- BackgroundTasks-ni kiritamiz
    db: Session = Depends(get_db)
):
    db_user = db.query(models.DbUser).filter(models.DbUser.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Ushbu foydalanuvchi nomi band")
    
    hashed_pwd = auth.get_password_hash(user.password)
    role = user.role if user.role in ["admin", "user"] else "user"
    
    new_user = models.DbUser(username=user.username, hashed_password=hashed_pwd, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Orqa fonda bajariladigan vazifani qo'shamiz
    background_tasks.add_task(send_welcome_email, new_user.username) # pyright: ignore[reportArgumentType]
    
    return new_user


# 2. Login
@app.post("/token", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.DbUser).filter(models.DbUser.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password): # pyright: ignore[reportArgumentType]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi nomi yoki parol xato"
        )
    
    access_token = auth.create_access_token(data={"sub": user.username})
    refresh_token = auth.create_refresh_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# 3. Refresh Token
@app.post("/refresh", response_model=schemas.Token)
def refresh_token(payload: schemas.TokenRefreshRequest, db: Session = Depends(get_db)):
    token_data = auth.verify_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Yaroqsiz token turi")
        
    username = token_data.get("sub")
    user = db.query(models.DbUser).filter(models.DbUser.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
        
    new_access = auth.create_access_token(data={"sub": user.username})
    new_refresh = auth.create_refresh_token(data={"sub": user.username})
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }


# 4. Profil ma'lumotlarini olish
@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.DbUser = Depends(auth.get_current_user)):
    return current_user


# 5. Mahsulot yaratish (Yaratuvchining ID-si `owner_id` bilan birga saqlanadi)
@app.post("/items/", response_model=schemas.ItemResponse)
def create_item(
    item: schemas.ItemCreate, 
    db: Session = Depends(get_db),
    current_user: models.DbUser = Depends(auth.get_current_user) # Tizimga kirgan foydalanuvchini olamiz
):
    # Faqat admin va superadmin yaratish huquqiga ega
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Sizda ruxsat yo'q!")
        
    db_item = models.DbItem(
        name=item.name, 
        price=item.price, 
        description=item.description,
        owner_id=current_user.id # Mahsulot egasining ID-sini yozamiz
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


# 6. Barcha mahsulotlarni olish
@app.get("/items/", response_model=List[schemas.ItemResponse])
def read_items(
    skip: int = 0, 
    limit: int = 10, 
    db: Session = Depends(get_db),
    current_user: models.DbUser = Depends(auth.get_current_user)
):
    items = db.query(models.DbItem).offset(skip).limit(limit).all()
    return items
