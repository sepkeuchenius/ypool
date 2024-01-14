# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app
from firebase_admin import storage, db, auth
import datetime
import numpy as np
from elopy.elo import Elo
from matplotlib import pyplot
from typing import Dict
import mpld3

initialize_app()
user_ref = db.reference("users")
matches_ref = db.reference("matches")

#
#
# @https_fn.on_request()
# def on_request_example(req: https_fn.Request) -> https_fn.Response:
#     return https_fn.Response("Hello world!")


@https_fn.on_call()
def on_request_example(req: https_fn.CallableRequest) -> https_fn.Response:
    return "Hoi"


@https_fn.on_call()
def create_user_account(req: https_fn.CallableRequest):
    print(req)
    if not user_ref.child(req.auth.uid).get():
        user_ref.update({req.auth.uid: {"name": req.data["username"]}})
    return req.auth.uid, user_ref.child(req.auth.uid).get()


@https_fn.on_call()
def get_all_users(req: https_fn.CallableRequest):
    return [{"uid": uid, "name": d["name"]} for uid, d in user_ref.get().items()]


@https_fn.on_call()
def save_match(req: https_fn.CallableRequest):
    print(req)
    winner = req.data["opponent"] if req.data["outcome"] == "lost" else req.auth.uid
    loser = req.data["opponent"] if winner == req.auth.uid else req.auth.uid
    matches_ref.push(
        {
            "winner": winner,
            "loser": loser,
            "issuer": req.auth.uid,
            "datetime": datetime.datetime.now().isoformat(),
        }
    )
    return "OK"


@https_fn.on_call()
def get_score(req: https_fn.CallableRequest):
    matches = matches_ref.get().values()
    uid2names = {uid: userinfo["name"] for uid, userinfo in user_ref.get().items()}
    return [
        {
            "winner": uid2names[match["winner"]],
            "loser": uid2names[match["loser"]],
            "issuer": uid2names[match["issuer"]],
        }
        for match in matches
    ]


@https_fn.on_call()
def user_exists(req: https_fn.CallableRequest):
    return (
        len(auth.get_users(identifiers=[auth.EmailIdentifier(req.data["email"])]).users)
        > 0
    )


@https_fn.on_call()
def create_user(req: https_fn.CallableRequest):
    return auth.create_user(
        email=req.data["email"],
        display_name=req.data["display_name"],
        password=req.data["password"],
    ).uid


@https_fn.on_call()
def get_elo_ratings(req: https_fn.CallableRequest):
    matches = _get_matches()
    players: Dict[str, Elo] = {}
    for match in matches:
        if match["winner"] not in players:
            players[match["winner"]] = Elo(k=32)
        if match["loser"] not in players:
            players[match["loser"]] = Elo(k=32)
        players[match["winner"]].play_game(players[match["loser"]], 1)
    return sorted(
        [(_get_username(player), players[player].elo) for player in players],
        key=lambda x: x[1],
        reverse=True,
    )


def _get_username(uid):
    return user_ref.child(uid).get().get("name")


def _get_matches() -> list:
    return matches_ref.get().values()


def _count(subject, action, counter) -> dict:
    if subject in counter and action in counter[subject]:
        counter[subject][action] += 1
    elif subject in counter:
        counter[subject][action] = 1
    else:
        counter[subject] = {}
        counter[subject][action] = 1
    return counter


@https_fn.on_call()
def get_bar_chart(req: https_fn.CallableRequest):
    matches = _get_matches()
    chart_data = {}
    for match in matches:
        chart_data = _count(match["winner"], "winner", chart_data)
        chart_data = _count(match["winner"], "player", chart_data)
        chart_data = _count(match["loser"], "loser", chart_data)
        chart_data = _count(match["loser"], "player", chart_data)

    players = chart_data.keys()
    players_data = {
        "wins": [
            chart_data[player]["winner"] if "winner" in chart_data[player] else 0
            for player in players
        ],
        "losses": [
            chart_data[player]["loser"] if "loser" in chart_data[player] else 0
            for player in players
        ],
        "plays": [
            chart_data[player]["player"] if "player" in chart_data[player] else 0
            for player in players
        ],
    }
    x = np.arange(len(players))
    width = 0.1
    fig, ax = pyplot.subplots(layout="constrained")

    for index, (attribute, values) in enumerate(players_data.items()):
        rects = ax.bar(x + width * index, values, width, label=attribute)
        ax.bar_label(rects, padding=0)

    ax.set_xticks(width + x, map(_get_username, players))
    ax.legend(loc="upper left", ncols=3)

    fig.set_size_inches(
        (req.data["w"] - 50) / 96,
        (req.data["w"] - 50) / 96,
    )
    return mpld3.fig_to_html(fig)
