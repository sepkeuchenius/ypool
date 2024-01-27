# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app
from firebase_admin import storage, db, auth, messaging, credentials
import datetime
from elopy.elo import Elo
from typing import Dict, List

# cert = credentials.Certificate(cert="ypool-generic-platform-firebase-adminsdk-fmr6u-5f64267170.json")
app = initialize_app()
user_ref = db.reference("users")
matches_ref = db.reference("matches")
elos_ref = db.reference("elos")

LEARNING_RATE = 32

@https_fn.on_call()
def subscribe_to_pool(req: https_fn.CallableRequest):
    return {
        "SUCCESS": messaging.subscribe_to_topic(
            req.data["tokens"], "pool"
        ).success_count
        == len(req.data["tokens"])
    }


@https_fn.on_call()
def notify_success(req: https_fn.CallableRequest):
    return messaging.send(
        messaging.Message(
            notification=messaging.Notification("title", "content"),
            token=req.data["token"],
        )
    )


@https_fn.on_call()
def send_test_notification(req: https_fn.CallableRequest):
    return messaging.send(
        messaging.Message(
            data={"title": "test"},
            topic="pool",
            notification=messaging.Notification("title", "content"),
        )
    )


@https_fn.on_call()
def get_all_users(req: https_fn.CallableRequest):
    return _get_users()


def _get_users():
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
    elos_ref.push(_calc_new_elo_rating(winner, loser))
    return "OK"


def _calc_new_elo_rating(winner, loser):
    rating: dict = list(elos_ref.get().values())[-1]
    winner_elo = Elo(start_elo=rating.get(winner), k=LEARNING_RATE)
    loser_elo = Elo(start_elo=rating.get(loser), k=LEARNING_RATE)
    winner_elo.play_game(loser_elo, 1)
    rating[winner] = winner_elo.elo
    rating[loser] = loser_elo.elo
    return rating


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
def get_elo_ratings(req: https_fn.CallableRequest) -> list:
    players, history = _get_elo_table()
    return {
        "ranking": sorted(
            [(_get_username(player), players[player].elo) for player in players],
            key=lambda x: x[1],
            reverse=True,
        ),
        "history": _rewrite_scores(history),
    }


def _rewrite_scores(score_history):
    players_history = {_get_username(user): [] for user in score_history[0]}
    for match in score_history:
        for player in match:
            players_history[_get_username(player)].append(match[player])
    return players_history


def _remove_passive_players(rating_history: List[dict]):
    passive_players = list(rating_history[-1].keys())
    for rating in rating_history:
        for player in rating:
            if player in passive_players and rating[player] != 1500:
                passive_players.remove(player)  # this player is not passive
    for rating in rating_history:
        for player in passive_players:
            del rating[player]
    return rating_history


def _get_elo_table() -> Dict[str, Elo]:
    rating_history = list(elos_ref.get().values())
    rating_history = _remove_passive_players(rating_history)
    rating = rating_history[-1].copy()
    for player in rating:
        rating[player] = Elo(start_elo=rating[player], k=LEARNING_RATE)
    return rating, rating_history


@https_fn.on_call()
def get_most_efficient_opponent(req: https_fn.CallableRequest):
    user_elo_ratings, _ = _get_elo_table()
    user_rating = user_elo_ratings.get(req.auth.uid)
    if not user_rating:
        return {"most_efficient_opponent": None, "potential_elo": None}
    current_best_opponent = None
    current_best_potential_elo = 0
    for player in user_elo_ratings:
        if player == req.auth.uid:
            continue  # cant play myself
        user_potential_elo = Elo(start_elo=user_rating.elo, k=LEARNING_RATE)
        opponent_potential_elo = Elo(start_elo=user_elo_ratings[player].elo, k=LEARNING_RATE)
        user_potential_elo.play_game(opponent_potential_elo, 1)
        if user_potential_elo.elo > current_best_potential_elo:
            current_best_opponent = player
            current_best_potential_elo = user_potential_elo.elo
            new_ratings = user_elo_ratings.copy()
            new_ratings[req.auth.uid] = user_potential_elo
            new_ratings[current_best_opponent] = opponent_potential_elo
            print(
                sorted(
                    [
                        (_get_username(player), new_ratings[player].elo)
                        for player in new_ratings
                    ],
                    key=lambda x: x[1],
                    reverse=True,
                )
            )
            potential_place = [
                player
                for player, elo in sorted(
                    [(player, new_ratings[player].elo) for player in new_ratings],
                    key=lambda x: x[1],
                    reverse=True,
                )
            ].index(req.auth.uid)
    return {
        "most_efficient_opponent": _get_username(current_best_opponent),
        "potential_elo": current_best_potential_elo,
        "potential_place": potential_place + 1,
    }


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
