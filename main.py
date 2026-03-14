from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import secrets

from database import get_db, init_db, Game, Registration, GameResult
from telegram_notify import notify_new_registration
from config import ADMIN_USERNAME, ADMIN_PASSWORD, SECRET_KEY

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Simple in-memory session store
sessions: dict[str, bool] = {}


@app.on_event("startup")
def on_startup():
    init_db()


# ── helpers ──────────────────────────────────────────────────────────────────

def get_admin_session(request: Request) -> bool:
    token = request.cookies.get("admin_session")
    return bool(token and sessions.get(token))


def require_admin(request: Request):
    if not get_admin_session(request):
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})


# ── public pages ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    upcoming = (db.query(Game)
                .filter(Game.is_active == True, Game.game_date >= datetime.utcnow())
                .order_by(Game.game_date)
                .limit(3).all())
    return templates.TemplateResponse("index.html", {"request": request, "games": upcoming})


@app.get("/schedule", response_class=HTMLResponse)
async def schedule(request: Request, db: Session = Depends(get_db)):
    games = (db.query(Game)
             .filter(Game.is_active == True, Game.game_date >= datetime.utcnow())
             .order_by(Game.game_date).all())
    # count registered teams per game
    counts = {}
    for g in games:
        counts[g.id] = db.query(Registration).filter(Registration.game_id == g.id).count()
    return templates.TemplateResponse("schedule.html", {
        "request": request, "games": games, "counts": counts
    })


@app.get("/register/{game_id}", response_class=HTMLResponse)
async def register_form(game_id: int, request: Request, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id, Game.is_active == True).first()
    if not game:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    registered = db.query(Registration).filter(Registration.game_id == game_id).count()
    spots_left = game.max_teams - registered
    return templates.TemplateResponse("register.html", {
        "request": request, "game": game, "spots_left": spots_left
    })


@app.post("/register/{game_id}", response_class=HTMLResponse)
async def register_submit(
    game_id: int, request: Request, db: Session = Depends(get_db),
    team_name: str = Form(...),
    contact_name: str = Form(...),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    players_count: int = Form(2),
    comment: Optional[str] = Form(None),
):
    game = db.query(Game).filter(Game.id == game_id, Game.is_active == True).first()
    if not game:
        raise HTTPException(status_code=404, detail="Игра не найдена")

    registered = db.query(Registration).filter(Registration.game_id == game_id).count()
    if registered >= game.max_teams:
        return templates.TemplateResponse("register.html", {
            "request": request, "game": game, "spots_left": 0,
            "error": "К сожалению, все места заняты."
        })

    reg = Registration(
        game_id=game_id,
        team_name=team_name,
        contact_name=contact_name,
        phone=phone,
        email=email,
        players_count=players_count,
        comment=comment,
    )
    db.add(reg)
    db.commit()

    await notify_new_registration(
        game_title=game.title,
        game_date=game.game_date.strftime("%d.%m.%Y %H:%M"),
        location=game.location,
        team_name=team_name,
        contact_name=contact_name,
        phone=phone or "",
        email=email or "",
        players_count=players_count,
    )

    return templates.TemplateResponse("success.html", {"request": request, "game": game})


@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(request: Request, db: Session = Depends(get_db)):
    # last 10 completed games with results
    games_with_results = (db.query(Game)
                          .filter(Game.game_date < datetime.utcnow())
                          .order_by(Game.game_date.desc())
                          .limit(10).all())
    results = {}
    for g in games_with_results:
        results[g.id] = (db.query(GameResult)
                         .filter(GameResult.game_id == g.id)
                         .order_by(GameResult.place).all())
    return templates.TemplateResponse("leaderboard.html", {
        "request": request, "games": games_with_results, "results": results
    })


# ── admin ─────────────────────────────────────────────────────────────────────

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})


@app.post("/admin/login")
async def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = secrets.token_hex(32)
        sessions[token] = True
        response = RedirectResponse("/admin", status_code=303)
        response.set_cookie("admin_session", token, httponly=True, samesite="lax")
        return response
    return templates.TemplateResponse("admin/login.html", {
        "request": request, "error": "Неверный логин или пароль"
    })


@app.get("/admin/logout")
async def admin_logout(request: Request):
    token = request.cookies.get("admin_session")
    if token:
        sessions.pop(token, None)
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie("admin_session")
    return response


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    total_games = db.query(Game).count()
    total_regs = db.query(Registration).count()
    upcoming = (db.query(Game)
                .filter(Game.is_active == True, Game.game_date >= datetime.utcnow())
                .order_by(Game.game_date).limit(5).all())
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "total_games": total_games,
        "total_regs": total_regs,
        "upcoming": upcoming,
    })


@app.get("/admin/games", response_class=HTMLResponse)
async def admin_games(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    games = db.query(Game).order_by(Game.game_date.desc()).all()
    counts = {g.id: db.query(Registration).filter(Registration.game_id == g.id).count()
              for g in games}
    return templates.TemplateResponse("admin/games.html", {
        "request": request, "games": games, "counts": counts
    })


@app.get("/admin/games/new", response_class=HTMLResponse)
async def admin_game_new(request: Request):
    require_admin(request)
    return templates.TemplateResponse("admin/game_form.html", {"request": request, "game": None})


@app.post("/admin/games/new")
async def admin_game_create(
    request: Request, db: Session = Depends(get_db),
    title: str = Form(...),
    game_type: str = Form(...),
    location: str = Form(...),
    address: Optional[str] = Form(None),
    game_date: str = Form(...),
    max_teams: int = Form(20),
    price: int = Form(0),
    description: Optional[str] = Form(None),
):
    require_admin(request)
    game = Game(
        title=title, game_type=game_type, location=location, address=address,
        game_date=datetime.strptime(game_date, "%Y-%m-%dT%H:%M"),
        max_teams=max_teams, price=price, description=description,
    )
    db.add(game)
    db.commit()
    return RedirectResponse("/admin/games", status_code=303)


@app.get("/admin/games/{game_id}/edit", response_class=HTMLResponse)
async def admin_game_edit(game_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("admin/game_form.html", {"request": request, "game": game})


@app.post("/admin/games/{game_id}/edit")
async def admin_game_update(
    game_id: int, request: Request, db: Session = Depends(get_db),
    title: str = Form(...),
    game_type: str = Form(...),
    location: str = Form(...),
    address: Optional[str] = Form(None),
    game_date: str = Form(...),
    max_teams: int = Form(20),
    price: int = Form(0),
    description: Optional[str] = Form(None),
    is_active: Optional[str] = Form(None),
):
    require_admin(request)
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404)
    game.title = title
    game.game_type = game_type
    game.location = location
    game.address = address
    game.game_date = datetime.strptime(game_date, "%Y-%m-%dT%H:%M")
    game.max_teams = max_teams
    game.price = price
    game.description = description
    game.is_active = is_active == "on"
    db.commit()
    return RedirectResponse("/admin/games", status_code=303)


@app.get("/admin/registrations", response_class=HTMLResponse)
async def admin_registrations(request: Request, game_id: Optional[int] = None,
                               db: Session = Depends(get_db)):
    require_admin(request)
    query = db.query(Registration)
    if game_id:
        query = query.filter(Registration.game_id == game_id)
    regs = query.order_by(Registration.created_at.desc()).all()
    games = db.query(Game).order_by(Game.game_date.desc()).all()
    games_map = {g.id: g for g in games}
    return templates.TemplateResponse("admin/registrations.html", {
        "request": request, "regs": regs, "games": games,
        "games_map": games_map, "filter_game_id": game_id
    })


@app.post("/admin/registrations/{reg_id}/confirm")
async def admin_confirm_reg(reg_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    reg = db.query(Registration).filter(Registration.id == reg_id).first()
    if reg:
        reg.is_confirmed = not reg.is_confirmed
        db.commit()
    return RedirectResponse("/admin/registrations", status_code=303)


@app.get("/admin/results", response_class=HTMLResponse)
async def admin_results(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    past_games = (db.query(Game)
                  .filter(Game.game_date < datetime.utcnow())
                  .order_by(Game.game_date.desc()).all())
    results = {g.id: db.query(GameResult).filter(GameResult.game_id == g.id)
                                         .order_by(GameResult.place).all()
               for g in past_games}
    return templates.TemplateResponse("admin/results.html", {
        "request": request, "games": past_games, "results": results
    })


@app.post("/admin/results/{game_id}")
async def admin_results_save(
    game_id: int, request: Request, db: Session = Depends(get_db),
):
    require_admin(request)
    form = await request.form()
    # delete old results for this game
    db.query(GameResult).filter(GameResult.game_id == game_id).delete()
    # parse rows: team_name_1, place_1, score_1 ...
    i = 1
    while f"team_name_{i}" in form:
        name = form.get(f"team_name_{i}", "").strip()
        place = form.get(f"place_{i}", "")
        score = form.get(f"score_{i}", "")
        if name and place:
            db.add(GameResult(
                game_id=game_id,
                team_name=name,
                place=int(place),
                score=int(score) if score else None,
            ))
        i += 1
    db.commit()
    return RedirectResponse("/admin/results", status_code=303)
