import app.roulette as roulette

from flask import (
    Blueprint,
    flash,
    g,
    json,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from app.auth import login_required
from app.db import get_db

import matplotlib
matplotlib.use("Agg")
import io
import base64
import matplotlib.pyplot as plt


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
    weights = [1.0] * 37
    game = roulette.Game(player, weights=weights)

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
    db.execute("UPDATE user SET balance = ? WHERE id = ?", (new_balance, g.user["id"]))
    db.commit()

    return jsonify({"success": True, "new_balance": new_balance})


def generate_winnings_walk_plot(winnings_list):
    """
    winnings_list: list of cumulative winnings or balance after each spin
    """
    fig, ax = plt.subplots(figsize=(15, 3))
    ax.plot(range(1, len(winnings_list) + 1), winnings_list, color="blue", linewidth=2)
    ax.set_title("Random Walk of Winnings")
    ax.set_xlabel("Spin Number")
    ax.set_ylabel("Balance / Total Winnings")
    ax.grid(True)

    plt.tight_layout()

    # Save to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    # Convert to base64 string to send in JSON
    img_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return img_base64


@bp.route("/simulation", methods=["GET", "POST"])
@login_required
def simulation():
    db = get_db()
    weights_row = db.execute(
        "SELECT weights FROM user WHERE id = ?", (g.user["id"],)
    ).fetchone()
    weights = [1.0] * 37
    if weights_row and weights_row["weights"]:
        try:
            weights = json.loads(weights_row["weights"])
        except Exception:
            pass

    if request.method == "GET":
        return render_template("index/simulation.html", weights=weights)

    data = request.get_json()
    runs = int(data.get("runs", 1000))
    balance = float(data.get("balance", 1000000))
    bets_data = data.get("bets", [])

    if not bets_data:
        return jsonify({"error": "No bets provided."}), 400

    # Convert JSON bets to Bet objects
    bets_template = [
        roulette.Bet(b["bet_type"], float(b["amount"]), b["choices"]) for b in bets_data
    ]

    # Initialize counters
    cumulative_winnings = []
    current_balance = balance
    number_count = [0] * 37
    color_count = {"red": 0, "black": 0, "green": 0}

    # Run the simulation
    for _ in range(runs):
        # Make fresh copy of bets for this spin
        spin_bets = [
            roulette.Bet(b.bet_type, b.amount, b.choices) for b in bets_template
        ]
        # Create a new player for each spin to track balance locally
        player = roulette.Player(current_balance)
        for b in spin_bets:
            player.place_bet(b)
        # Create a new game and spin
        game = roulette.Game(player, weights=weights)
        number, color, winnings = game.spin_wheel()
        current_balance = player.balance
        cumulative_winnings.append(current_balance)

        number_count[number] += 1
        color_count[color] += 1

    plot_img = generate_winnings_walk_plot(cumulative_winnings)

    return jsonify(
        {
            "total_winnings": current_balance - balance,
            "number_count": number_count,
            "color_count": color_count,
            "plot": plot_img,
        }
    )


@bp.route("/api/update_weights", methods=["POST"])
@login_required
def update_weights():
    data = request.get_json()
    weights = data.get("weights")
    if not weights or len(weights) != 37:
        return jsonify({"success": False, "message": "Invalid weights"}), 400

    db = get_db()
    db.execute(
        "UPDATE user SET weights = ? WHERE id = ?", (json.dumps(weights), g.user["id"])
    )
    db.commit()
    return jsonify({"success": True})
