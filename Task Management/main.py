from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from firebase_admin.auth import UserNotFoundError
from firebase_admin._auth_utils import UserNotFoundError
from fastapi import HTTPException
from firebase.firebase_config import db, auth, bucket
from firebase_admin import auth as firebase_auth, firestore
from datetime import datetime
from fastapi import Form, HTTPException
from google.cloud import firestore
from fastapi.responses import Response

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Helper Functions
def validateFirebaseToken(id_token):
    try:
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded
    except:
        return None


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


# Routes
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register_user(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        user = firebase_auth.create_user(email=email, password=password)
        db.collection("users").document(user.uid).set({
            "uid": user.uid,
            "email": email,
            "boards": []
        })
        return RedirectResponse("/", status_code=302)
    except Exception as e:
        return templates.TemplateResponse("register.html", {"request": request, "error": str(e)})


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


@app.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("token")
    return response


# Board CRUD
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


@app.post("/rename-board/{board_id}")
async def rename_board(request: Request, board_id: str, new_name: str = Form(...)):
    token = request.cookies.get("token")
    user = getUser(token)
    board = db.collection("taskboards").document(board_id).get().to_dict()
    if board["owner"] != user["uid"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    db.collection("taskboards").document(board_id).update({"name": new_name})
    return RedirectResponse(f"/board/{board_id}", status_code=302)


@app.post("/delete-board/{board_id}")
async def delete_board(request: Request, board_id: str):
    token = request.cookies.get("token")
    user = getUser(token)
    board_ref = db.collection("taskboards").document(board_id)
    board = board_ref.get().to_dict()
    if board["owner"] != user["uid"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Remove users
    for u in board["users"]:
        if u != user["uid"]:
            board_ref.update({"users": db.ArrayRemove([u])})

    # Remove tasks
    tasks = board_ref.collection("tasks").stream()
    for task in tasks:
        task.reference.delete()

    board_ref.delete()
    return RedirectResponse("/main", status_code=302)


# Board View
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

    tasks = board_ref.collection("tasks").stream()
    tasks = [t.to_dict() | {"id": t.id} for t in tasks]

    # Fetch full user details for members
    members = []
    for uid in board_data["users"]:
        user_doc = db.collection("users").document(uid).get()
        if user_doc.exists:
            user_info = user_doc.to_dict()
            members.append({
                "uid": user_info.get("uid", uid),
                "email": user_info.get("email", "N/A")
            })

    return templates.TemplateResponse("board.html", {
        "request": request,
        "board": board_data | {"id": board_id},
        "tasks": tasks,
        "user": user,
        "members": members
    })



# Task CRUD
@app.post("/board/{board_id}/add-task")
async def add_task(request: Request, board_id: str, title: str = Form(...), due: str = Form(...)):
    task_ref = db.collection("taskboards").document(board_id).collection("tasks").document()
    task_ref.set({
        "title": title,
        "due": due,
        "complete": False,
        "completed_at": None,
        "assigned_users": []
    })
    return RedirectResponse(f"/board/{board_id}", status_code=302)


@app.post("/board/{board_id}/task/{task_id}/toggle")
async def toggle_task(request: Request, board_id: str, task_id: str):
    task_ref = db.collection("taskboards").document(board_id).collection("tasks").document(task_id)
    task = task_ref.get().to_dict()
    new_state = not task["complete"]
    task_ref.update({
        "complete": new_state,
        "completed_at": datetime.utcnow() if new_state else None
    })
    return RedirectResponse(f"/board/{board_id}", status_code=302)


@app.post("/board/{board_id}/task/{task_id}/delete")
async def delete_task(request: Request, board_id: str, task_id: str):
    db.collection("taskboards").document(board_id).collection("tasks").document(task_id).delete()
    return RedirectResponse(f"/board/{board_id}", status_code=302)


@app.post("/board/{board_id}/task/{task_id}/edit")
async def edit_task(request: Request, board_id: str, task_id: str, title: str = Form(...), due: str = Form(...)):
    db.collection("taskboards").document(board_id).collection("tasks").document(task_id).update({
        "title": title,
        "due": due
    })
    return RedirectResponse(f"/board/{board_id}", status_code=302)


@app.post("/board/{board_id}/add-user")
async def add_user_to_board(request: Request, board_id: str, user_email: str = Form(...)):
    token = request.cookies.get("token")
    user = getUser(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_to_add = firebase_auth.get_user_by_email(user_email)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")

    board_ref = db.collection("taskboards").document(board_id)
    board = board_ref.get()
    if not board.exists:
        raise HTTPException(status_code=404, detail="Board not found")

    board_data = board.to_dict()
    if user["uid"] != board_data["owner"]:
        raise HTTPException(status_code=403, detail="Only the owner can add users")

    if user_to_add.uid in board_data["users"]:
        raise HTTPException(status_code=400, detail="User already added")

    board_ref.update({"users": firestore.ArrayUnion([user_to_add.uid])})

    return RedirectResponse(url=f"/board/{board_id}", status_code=303)


@app.post("/board/{board_id}/remove-user")
async def remove_user_from_board(request: Request, board_id: str, user_id: str = Form(...)):
    token = request.cookies.get("token")
    current_user = getUser(token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    board_ref = db.collection("taskboards").document(board_id)
    board = board_ref.get()
    if not board.exists:
        raise HTTPException(status_code=404, detail="Board not found")

    board_data = board.to_dict()
    if current_user["uid"] != board_data["owner"]:
        raise HTTPException(status_code=403, detail="Only the owner can remove users")

    if user_id == board_data["owner"]:
        raise HTTPException(status_code=400, detail="Cannot remove the board owner")

    board_ref.update({"users": firestore.ArrayRemove([user_id])})
    return RedirectResponse(url=f"/board/{board_id}", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
