# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app
from firebase_admin import storage, db, auth
import datetime
from elopy.elo import Elo
from typing import Dict

initialize_app()
user_ref = db.reference("users")
matches_ref = db.reference("matches")

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


def _create_user_account(uid, name):
    if not user_ref.child(uid).get():
        user_ref.update({uid: {"name": name}})
    return uid, user_ref.child(uid).get()


@https_fn.on_call()
def create_user(req: https_fn.CallableRequest):
    uid = auth.create_user(
        email=req.data["email"],
        display_name=req.data["display_name"],
        password=req.data["password"],
    ).uid
    _create_user_account(uid, req.data["display_name"])
    return uid


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
        chart_data = _count(match["loser"], "loser", chart_data)

    players = list(
        sorted(
            chart_data, key=lambda x: chart_data.get(x).get("winner", 0), reverse=True
        )
    )
    players_data = {
        "Wins": [
            chart_data[player]["winner"] if "winner" in chart_data[player] else 0
            for player in players
        ],
        "Losses": [
            chart_data[player]["loser"] if "loser" in chart_data[player] else 0
            for player in players
        ],
    }

    return {
        "labels": list(map(_get_username, players)),
        "sets": [
            {"label": label, "data": players_data[label]} for label in players_data
        ],
    }
