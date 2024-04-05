from firebase_functions import https_fn
from firebase_admin import initialize_app
from typing import List

app = initialize_app()

START_ELO = 1500
LEARNING_RATE = 32
USERNAMES = None
LLM = None
LLM_PARAMS = {
    "candidate_count": 1,
    "max_output_tokens": 1024,
    "temperature": 0.2,
    "top_p": 0.8,
    "top_k": 40,
}


def _load_llm():
    global LLM
    if not LLM:
        import vertexai
        from vertexai.language_models import TextGenerationModel
        from firebase_admin import credentials

        vertexai.init(
            project="ypool-generic-platform",
            location="us-central1",
            credentials=credentials.ApplicationDefault().get_credential(),
        )
        LLM = TextGenerationModel.from_pretrained("text-bison")
    return LLM


def generate_text(prompt):
    llm = _load_llm()
    response = llm.predict(
        prompt,
        **LLM_PARAMS,
    )
    return response.text


@https_fn.on_call(region="europe-west1")
def register_token(req: https_fn.CallableRequest):
    from firebase_admin import messaging, db

    user_ref = db.reference("users")
    if (
        not user_ref.child(req.auth.uid).get().get("notification-tokens")
        or req.data["token"]
        not in user_ref.child(req.auth.uid).child("notification-tokens").get().values()
    ):
        user_ref.child(req.auth.uid).child("notification-tokens").push(
            req.data["token"]
        )
        notify_success(req)
        messaging.subscribe_to_topic(req.data["token"], "pool").success_count


def notify_success(req: https_fn.CallableRequest):
    from firebase_admin import messaging

    return messaging.send(
        messaging.Message(
            data={
                "title": "Yeah!",
                "body": "You're setup to receive notifications.",
            },
            token=req.data["token"],
        )
    )


@https_fn.on_call(region="europe-west1")
def get_all_users(req: https_fn.CallableRequest):
    return _get_users()


def _get_users():
    usernames = _get_usernames()
    return [{"uid": uid, "name": d["name"]} for uid, d in usernames.items()]


def send_pool_notification(title, content):
    from firebase_admin import messaging

    messaging.send(
        messaging.Message(
            topic="pool",
            data={"title": title, "body": content},
        )
    )


@https_fn.on_call(region="europe-west1")
def save_match(req: https_fn.CallableRequest):
    import datetime
    from firebase_admin import db

    winner = req.data["opponent"] if req.data["outcome"] == "lost" else req.auth.uid
    loser = req.data["opponent"] if winner == req.auth.uid else req.auth.uid
    db.reference("matches").push(
        {
            "winner": winner,
            "loser": loser,
            "issuer": req.auth.uid,
            "datetime": datetime.datetime.now().isoformat(),
        }
    )
    elos_ref = db.reference("elos")
    elos_ref.push(_calc_new_elo_rating(winner, loser))
    joke = generate_text(
        f"Make a joke of 10 words, making fun of {_get_username(winner)} winning a game against {_get_username(loser)}"
    )
    send_pool_notification(
        "New game has been played!",
        f"{joke}\n{_get_username(winner)} just beat {_get_username(loser)}",
    )
    return "OK"


def _calc_new_elo_rating(winner, loser):
    from elopy.elo import Elo
    from firebase_admin import db

    elos_ref = db.reference("elos")
    rating: dict = list(elos_ref.get().values())[-1]
    winner_elo = Elo(start_elo=rating.get(winner, START_ELO), k=LEARNING_RATE)
    loser_elo = Elo(start_elo=rating.get(loser, START_ELO), k=LEARNING_RATE)
    winner_elo.play_game(loser_elo, 1)
    rating[winner] = winner_elo.elo
    rating[loser] = loser_elo.elo
    return rating


@https_fn.on_call(region="europe-west1")
def get_score(req: https_fn.CallableRequest):
    matches = _get_matches()
    usernames = _get_usernames()
    uid2names = {uid: userinfo["name"] for uid, userinfo in usernames.items()}
    return [
        {
            "winner": uid2names[match["winner"]],
            "loser": uid2names[match["loser"]],
            "issuer": uid2names[match["issuer"]],
        }
        for match in matches
    ]


@https_fn.on_call(region="europe-west1")
def user_exists(req: https_fn.CallableRequest):
    from firebase_admin import auth

    return (
        len(auth.get_users(identifiers=[auth.EmailIdentifier(req.data["email"])]).users)
        > 0
    )


def _create_user_account(uid, name):
    from firebase_admin import db

    user_ref = db.reference("users")
    if not user_ref.child(uid).get():
        user_ref.update({uid: {"name": name}})
    return uid, user_ref.child(uid).get()


@https_fn.on_call(region="europe-west1")
def create_user(req: https_fn.CallableRequest):
    from firebase_admin import auth

    uid = auth.create_user(
        email=req.data["email"],
        display_name=req.data["display_name"],
        password=req.data["password"],
    ).uid
    _create_user_account(uid, req.data["display_name"])
    return uid


@https_fn.on_call(region="europe-west1")
def get_elo_ratings(req: https_fn.CallableRequest) -> list:
    players, history, last_plays = _get_elo_table()
    return {
        "ranking": sorted(
            [(_get_username(player), players[player].elo) for player in players],
            key=lambda x: x[1],
            reverse=True,
        ),
        "history": _rewrite_scores(history),
        "last_plays": {_get_username(player): last_plays[player] for player in last_plays}
    }


def _rewrite_scores(score_history: List[dict]):
    players_history = {_get_username(user): [] for user in score_history[-1]}
    for rating in score_history:
        for player in score_history[-1]:
            player_history = players_history[_get_username(player)]
            player_history.append(rating.get(player))
            if (
                len(player_history) >= 2
                and player_history[-1] is not None
                and player_history[-2] is None
            ):
                player_history[-2] = START_ELO
    return players_history


def _remove_passive_players(rating_history: List[dict]):
    passive_players = list(rating_history[-1].keys())
    for rating in rating_history:
        for player in rating:
            if player in passive_players and rating[player] != START_ELO:
                passive_players.remove(player)  # this player is not passive
    for rating in rating_history:
        for player in passive_players:
            del rating[player]
    return rating_history


def _find_last_play(matches: List[dict], uid):
    import datetime
    for _match in reversed(matches):
        if uid in _match.values():  # winner loser or issuer
            return (datetime.datetime.now() - datetime.datetime.fromisoformat(_match.get("datetime"))).days


def _get_elo_table():
    from elopy.elo import Elo
    from firebase_admin import db

    matches = _get_matches()
    elos_ref = db.reference("elos")
    rating_history = list(elos_ref.get().values())
    rating_history = _remove_passive_players(rating_history)
    rating = rating_history[-1].copy()
    last_plays = {
        player: _find_last_play(matches, player) for player in rating
    }
    for player in rating:
        rating[player] = Elo(start_elo=rating[player], k=LEARNING_RATE)
    return rating, rating_history, last_plays


@https_fn.on_call(region="europe-west1")
def get_most_efficient_opponent(req: https_fn.CallableRequest):
    from elopy.elo import Elo

    user_elo_ratings, _, _ = _get_elo_table()
    user_rating = user_elo_ratings.get(req.auth.uid)
    if not user_rating:
        return {"most_efficient_opponent": None, "potential_elo": None}
    current_best_opponent = None
    current_best_potential_elo = 0
    for player in user_elo_ratings:
        if player == req.auth.uid:
            continue  # cant play myself
        user_potential_elo = Elo(start_elo=user_rating.elo, k=LEARNING_RATE)
        opponent_potential_elo = Elo(
            start_elo=user_elo_ratings[player].elo, k=LEARNING_RATE
        )
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


def _get_usernames():
    global USERNAMES
    if not USERNAMES:
        return _reload_usernames()
    else:
        return USERNAMES


def _reload_usernames():
    from firebase_admin import db

    global USERNAMES
    USERNAMES = db.reference("users").get()
    return USERNAMES


def _get_username(uid):
    _get_usernames()
    return (
        USERNAMES.get(uid, {}).get("name")
        if uid in USERNAMES
        else _reload_usernames().get(uid, {}).get("name")
    )


def _get_matches() -> list:
    from firebase_admin import db

    return db.reference("matches").get().values()


def _count(subject, action, counter) -> dict:
    if subject in counter and action in counter[subject]:
        counter[subject][action] += 1
    elif subject in counter:
        counter[subject][action] = 1
    else:
        counter[subject] = {}
        counter[subject][action] = 1
    return counter


@https_fn.on_call(region="europe-west1")
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
