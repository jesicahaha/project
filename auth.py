from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse #RedirectResponse 用於跳轉到其他頁面
import mysql.connector
import bcrypt #bcrypt：用來加密/驗證密碼

router = APIRouter()

db = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="raspberry",
    password="pi12345",
    database="test"
)
cursor = db.cursor(dictionary=True)

@router.get("/", response_class=HTMLResponse)
def login_page():
    with open("templates/login.html", "r", encoding="utf-8") as f:
        return f.read()

#註冊新使用者
@router.post("/register")#... 代表必填，Form:從 HTML 表單提交過來的資料
def register(username: str = Form(...), password: str = Form(...)):
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    if cursor.fetchone():#返回查詢結果的第一筆資料，若有資料表示使用者已存在
        raise HTTPException(400, "使用者已存在")

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())#加密密碼
    cursor.execute(
        "INSERT INTO users (username, password) VALUES (%s,%s)",
        (username, hashed)
    )
    db.commit()
    return RedirectResponse("/", status_code=303)

#使用者登入
@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    #bcrypt.checkpw(...) → 將使用者輸入的密碼加密後，比對資料庫存的密碼哈希值
    if not user or not bcrypt.checkpw(password.encode(), user["password"].encode()):
        raise HTTPException(400, "登入失敗")

    request.session["username"] = username
    return RedirectResponse("/dashboard", status_code=303)

@router.get("/logout")#還沒用到 之後改
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
