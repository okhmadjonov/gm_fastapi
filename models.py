# models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship # <-- relationship ni import qilamiz
from database import Base

class DbUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    
    # User va Item o'rtasidagi bog'liqlik (Bir foydalanuvchi ko'p mahsulotga ega bo'lishi mumkin)
    items = relationship("DbItem", back_populates="owner")


class DbItem(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    quantity = Column(Integer, default=0, nullable=False)
    
    # Tashqi kalit (ForeignKey) - foydalanuvchining ID siga bog'lanadi
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Bazada eski ma'lumotlar borligi uchun nullable=True qilamiz
    owner = relationship("DbUser", back_populates="items")
