from fastapi import FastAPI, HTTPException, Form, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import OperationalError
from passlib.context import CryptContext
import uvicorn
import json
import os
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Generator, List
from datetime import datetime, timezone  # إضافة timezone

app = FastAPI(title="Financial Insights API", description="API for user authentication and financial data")

# إعداد CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# إعداد قاعدة البيانات
DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# تعريف النماذج (Tables)
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String)
    role = Column(String, default="Regular User")

class Suggestion(Base):
    __tablename__ = "suggestions"
    __table_args__ = {'extend_existing': True}  # إصلاح InvalidRequestError
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    suggestion = Column(Text, nullable=False)
    created_at = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())  # إصلاح DeprecationWarning

class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    report = Column(Text, nullable=False)
    quality = Column(Integer, nullable=False)
    created_at = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())  # إصلاح DeprecationWarning

# تهيئة قاعدة البيانات
def init_db():
    try:
        # إنشاء الجداول إذا لم تكن موجودة
        Base.metadata.create_all(bind=engine)
        
        with engine.connect() as connection:
            # التحقق من وجود عمود role
            result = connection.execute("PRAGMA table_info(users)")
            columns = [col['name'] for col in result.fetchall()]
            if 'role' not in columns:
                connection.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Regular User'")
                print("Added 'role' column to users table")
            
            # التحقق من وجود عمود email
            if 'email' not in columns:
                connection.execute("ALTER TABLE users ADD COLUMN email TEXT")
                connection.execute("UPDATE users SET email = username || '@default.com' WHERE email IS NULL")
                print("Added 'email' column to users table and set default emails")
            
            # التأكد من أن عمود email غير قابل للقيم الفارغة
            connection.execute("CREATE TABLE temp_users AS SELECT id, username, email, hashed_password, role FROM users")
            connection.execute("DROP TABLE users")
            connection.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT,
                    role TEXT DEFAULT 'Regular User'
                )
            """)
            connection.execute("INSERT INTO users SELECT * FROM temp_users")
            connection.execute("DROP TABLE temp_users")
            print("Ensured 'email' column is NOT NULL")
            
    except Exception as e:
        print(f"Error initializing database: {str(e)}")

init_db()

# إعدادات الأمان
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# نماذج Pydantic
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    username: str
    email: str
    role: str

class SuggestionCreate(BaseModel):
    username: str
    suggestion: str

class EvaluationCreate(BaseModel):
    username: str
    report: str
    quality: int

# الوظائف (Endpoints)
@app.post("/register")
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        if not username or not email or not password or not role:
            raise HTTPException(status_code=400, detail="Missing required fields")
        if role not in ["Regular User", "Expert", "Administrator"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'Regular User', 'Expert', or 'Administrator'")
       
        if db.query(User).filter(User.username == username).first():
            raise HTTPException(status_code=400, detail="Username already exists")
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already exists")
        hashed_password = get_password_hash(password)
        new_user = User(username=username, email=email, hashed_password=hashed_password, role=role)
        db.add(new_user)
        db.commit()
        return {"msg": "User registered successfully"}
    except OperationalError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}")

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        if not username or not password:
            raise HTTPException(status_code=400, detail="Missing username or password")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid username")
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Invalid password")
        return {"msg": f"Welcome {username}", "role": user.role, "email": user.email}
    except OperationalError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.get("/users", response_model=List[UserResponse])
async def get_users(db: Session = Depends(get_db)):
    try:
        users = db.query(User).all()
        return [{"username": user.username, "email": user.email, "role": user.role} for user in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")

@app.put("/users/{username}")
async def update_user_role(username: str, role: str, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if role not in ["Regular User", "Expert", "Administrator"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = role
        db.commit()
        return {"msg": f"Role updated for {username}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating user role: {str(e)}")

@app.delete("/users/{username}")
async def delete_user(username: str, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        db.delete(user)
        db.commit()
        return {"msg": f"User {username} deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")

@app.get("/data/cleaned")
async def get_cleaned_data():
    try:
        file_path = r"C:\Users\Fa\Desktop\Streamlit-Authentication-main\cleaned.json"
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Cleaned data file not found")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading cleaned data: {str(e)}")

@app.get("/data/financial_phrasebank")
async def get_financial_phrasebank_data():
    try:
        file_path = r"C:\Users\Fa\Desktop\Streamlit-Authentication-main\financial_phrasebank (2).json"
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Financial phrasebank data file not found")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading financial phrasebank data: {str(e)}")

@app.get("/data/apple")
async def get_apple_data():
    try:
        file_path = r"C:\Users\Fa\Desktop\Streamlit-Authentication-main\stock_AAPL-1.json"
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Apple data file not found")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading Apple data: {str(e)}")

@app.get("/data/meta")
async def get_meta_data():
    try:
        file_path = r"C:\Users\Fa\Desktop\Streamlit-Authentication-main\stock_META-1.json"
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Meta data file not found")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading Meta data: {str(e)}")

@app.get("/data/microsoft")
async def get_microsoft_data():
    try:
        file_path = r"C:\Users\Fa\Desktop\Streamlit-Authentication-main\stock_MSFT-1.json"
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Microsoft data file not found")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading Microsoft data: {str(e)}")

@app.post("/suggestions")
async def submit_suggestion(suggestion: SuggestionCreate, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == suggestion.username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        new_suggestion = Suggestion(username=suggestion.username, suggestion=suggestion.suggestion)
        db.add(new_suggestion)
        db.commit()
        return {"msg": "Suggestion received and stored successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error submitting suggestion: {str(e)}")

@app.post("/evaluations")
async def submit_evaluation(evaluation: EvaluationCreate, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == evaluation.username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not (1 <= evaluation.quality <= 5):
            raise HTTPException(status_code=400, detail="Quality must be between 1 and 5")
        new_evaluation = Evaluation(
            username=evaluation.username,
            report=evaluation.report,
            quality=evaluation.quality
        )
        db.add(new_evaluation)
        db.commit()
        return {"msg": "Evaluation received and stored successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error submitting evaluation: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
