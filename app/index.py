import app.roulette as roulette

from flask import (
    Blueprint,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from app.auth import login_required
from app.db import get_db


bp = Blueprint("index", __name__)


@bp.route("/")
@login_required
def index():
    db = get_db()
    balance = db.execute(
        "SELECT balance FROM user WHERE username = ?", (g.user["username"],)
    ).fetchone()
    return render_template("index/index.html", balance=balance)


@bp.route("/api/spin", methods=("POST",))
@login_required
def spin():
    db = get_db()

    player = roulette.Player(g.user["balance"])
    game = roulette.Game(player)

    bets = request.json.get("bets", [])
    if not bets:
        return jsonify({"error": "No bets placed."}), 400

    for bet in bets:
        try:
            bet_type = bet["bet_type"]
            amount = float(bet["amount"])
            choices = bet["choices"]
            new_bet = roulette.Bet(bet_type, amount, choices)
            if not player.place_bet(new_bet):
                return jsonify({"error": "Insufficient balance for bet."}), 400
        except (KeyError, ValueError):
            return jsonify({"error": "Invalid bet format."}), 400

    number, color, winnings = game.spin_wheel()

    new_balance = player.balance
    db.execute("UPDATE user SET balance = ? WHERE id = ?", (new_balance, g.user["id"]))
    db.commit()

    return jsonify(
        {
            "number": number,
            "color": color,
            "winnings": winnings,
            "balance": new_balance,
        }
    )


@bp.route("/api/topup", methods=["POST"])
@login_required
def topup():
    if not g.user:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    data = request.get_json()
    if not data or "amount" not in data:
        return jsonify({"success": False, "message": "Missing top-up amount."}), 400

    try:
        amount = float(data["amount"])
        if amount <= 0:
            raise ValueError
    except ValueError:
        return jsonify({"success": False, "message": "Invalid amount."}), 400

    db = get_db()
    new_balance = g.user["balance"] + amount
    db.execute(
        "UPDATE user SET balance = ? WHERE id = ?", (new_balance, g.user["id"])
    )
    db.commit()

    # Also update g.user so frontend sees the new balance immediately
    g.user["balance"] = new_balance

    return jsonify({"success": True, "new_balance": new_balance})

