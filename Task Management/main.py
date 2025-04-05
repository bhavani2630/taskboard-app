from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from firebase.firebase_config import db, auth, bucket
from firebase_admin import auth as firebase_auth
import os
import uuid
from local_constants import PROJECT_BUCKET
from starlette.responses import StreamingResponse
from datetime import datetime
import io

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Helper: Validate Firebase token
def validateFirebaseToken(id_token):
    try:
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded
    except:
        return None

# Helper: Get/Create user document
def getUser(token):
    decoded = validateFirebaseToken(token)
    if not decoded:
        return None
    uid = decoded['uid']
    user_ref = db.collection('users').document(uid)
    user = user_ref.get()
    if not user.exists:
        user_ref.set({
            'uid': uid,
            'email': decoded.get('email', ''),
            'boards': []
        })
    return user_ref.get().to_dict()

# Route: Register page
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Route: Handle registration form
@app.post("/register", response_class=HTMLResponse)
async def register_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        user = firebase_auth.create_user(email=email, password=password)
        db.collection("users").document(user.uid).set({
            "uid": user.uid,
            "email": email,
            "boards": []
        })
        return RedirectResponse("/", status_code=302)
    except Exception as e:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": str(e)
        })


# Route: Login page
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Route: Main dashboard
@app.get("/main", response_class=HTMLResponse)
async def main_page(request: Request):
    token = request.cookies.get("token")
    user = getUser(token)
    if not user:
        return RedirectResponse("/")
    
    boards_ref = db.collection('taskboards')
    user_boards = boards_ref.where("users", "array_contains", user['uid']).stream()
    boards = [b.to_dict() | {"id": b.id} for b in user_boards]
    return templates.TemplateResponse("main.html", {"request": request, "boards": boards, "user": user})

# Route: Create Task Board
@app.post("/add-board")
async def add_board(request: Request, board_name: str = Form(...)):
    token = request.cookies.get("token")
    user = getUser(token)
    if not user:
        return RedirectResponse("/")
    board_ref = db.collection('taskboards').document()
    board_ref.set({
        "name": board_name,
        "owner": user["uid"],
        "users": [user["uid"]],
        "created": datetime.utcnow()
    })
    return RedirectResponse("/main", status_code=302)

# Route: Task Board Page
@app.get("/board/{board_id}", response_class=HTMLResponse)
async def view_board(request: Request, board_id: str):
    token = request.cookies.get("token")
    user = getUser(token)
    if not user:
        return RedirectResponse("/")

    board_ref = db.collection("taskboards").document(board_id)
    board = board_ref.get()
    if not board.exists:
        return RedirectResponse("/main")

    board_data = board.to_dict()
    if user["uid"] not in board_data["users"]:
        return RedirectResponse("/main")

    tasks = db.collection("taskboards").document(board_id).collection("tasks").stream()
    tasks = [t.to_dict() | {"id": t.id} for t in tasks]

    return templates.TemplateResponse("board.html", {
        "request": request,
        "board": board_data | {"id": board_id},
        "tasks": tasks,
        "user": user
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
