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


from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_serializer
from typing import Optional, Self
import datetime as dt


class PlayedMatch(BaseModel):
    issuer: str
    winner: str
    loser: str
    datetime: Optional[dt.datetime] = Field(None)
    @field_serializer('winner')
    def serialize_winner(self, winner):
        return _get_username(winner)
    @field_serializer('loser')
    def serialize_loser(self, loser):
        return _get_username(loser)
    @field_serializer('issuer')
    def serialize_issuer(self, issuer):
        return _get_username(issuer)


class Match(BaseModel):
    players: list[str]
    counterpart: Optional[Self] = Field(None)
    played_match: Optional[PlayedMatch] = Field(None)
    
    @model_serializer
    def ser_model(self):
        return {"players": [_get_username(player) for player in self.players]}


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
            "winner": uid2names[match.winner],
            "loser": uid2names[match.loser],
            "issuer": uid2names[match.issuer],
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
    elo_table = _get_elo_table()
    return {
        "ranking": sorted(
            [
                (_get_username(player), elo_table.current_rating[player].elo)
                for player in elo_table.current_rating
            ],
            key=lambda x: x[1],
            reverse=True,
        ),
        "month_ranking": sorted(
            [
                (_get_username(player), elo_table.month_rating[player].elo)
                for player in elo_table.month_rating
            ],
            key=lambda x: x[1],
            reverse=True,
        ),
        "history": _rewrite_scores(elo_table.rating_history),
        "last_plays": {
            _get_username(player): elo_table.last_played_days_ago[player]
            for player in elo_table.last_played_days_ago
        },
    }


def _rewrite_scores(score_history: List[dict]):
    """
    Rewrite the scores to have a list of scores for each player
    To determine progression of each player over time
    """
    score_history = _remove_trailing_scores(score_history)
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


def _remove_trailing_scores(rating_history: List[dict]):
    last_ratings = rating_history[-1]
    players = list(last_ratings.keys())
    for i in range(len(rating_history) - 2, 0, -1):
        for player in players:
            if (
                player in last_ratings
                and rating_history[i].get(player) == last_ratings[player]
            ):
                del rating_history[i][player]
    for player in players:
        if not rating_history[len(rating_history) - 2].get(player):
            last_ratings[player] = None
    return rating_history


def _find_last_play(matches: List[PlayedMatch], uid):
    import datetime

    for _match in reversed(matches):
        if uid in _match.model_dump().values():  # winner loser or issuer
            return (datetime.datetime.now() - _match.datetime).days


def _get_elo_history():
    from firebase_admin import db

    elos_ref = db.reference("elos")
    rating_history = list(elos_ref.get().values())
    return rating_history


from elopy.elo import Elo


class EloTable(BaseModel):
    current_rating: dict[str, Elo]
    rating_history: list[dict]
    last_played_days_ago: dict[str, int]
    month_rating: dict[str, Elo]
    model_config = ConfigDict(arbitrary_types_allowed=True)


def _get_elo_table() -> EloTable:
    import datetime

    matches = _get_matches()
    rating_history = _get_elo_history()
    rating_history = _remove_passive_players(rating_history)
    now = datetime.datetime.now()
    rating = rating_history[-1].copy()
    match_played_this_month = False
    for i, match in enumerate(matches):
        if match.datetime and match.datetime.month == now.month:
            match_played_this_month = True
            break
    month_rating: dict[str, Elo] = {}
    for player in rating:
        month_rating[player] = Elo(start_elo=START_ELO, k=LEARNING_RATE)
    if match_played_this_month:
        for match in matches[i:]:
            month_rating[match.winner].play_game(month_rating[match.loser], 1)
    last_plays = {
        player: _find_last_play(matches, player) for player in rating
    }  # get the last play for each player to know when they last played
    for player in rating:
        rating[player] = Elo(start_elo=rating[player], k=LEARNING_RATE)

    return EloTable(
        current_rating=rating,
        rating_history=rating_history,
        last_played_days_ago=last_plays,
        month_rating=month_rating,
    )


@https_fn.on_call(region="europe-west1")
def get_most_efficient_opponent(req: https_fn.CallableRequest):
    from elopy.elo import Elo

    user_elo_ratings = _get_elo_table().current_rating
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


def _get_matches() -> list[PlayedMatch]:
    from firebase_admin import db

    return [
        PlayedMatch.model_validate(match)
        for match in db.reference("matches").get().values()
    ]


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
        chart_data = _count(match.winner, "winner", chart_data)
        chart_data = _count(match.loser, "loser", chart_data)

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


class MonthMatches(BaseModel):
    year: int
    month: int
    matches: list[PlayedMatch]
    last_elo: dict


def _calc_monthly_matches(
    matches: list[PlayedMatch], elos: list[dict]
) -> List[MonthMatches]:
    tournies: list[MonthMatches] = []
    for index, match in enumerate(matches):
        if match.datetime:
            if (
                len(tournies) > 0
                and match.datetime.year == tournies[-1].year
                and match.datetime.month == tournies[-1].month
            ):
                tournies[-1].matches.append(match)
                tournies[-1].last_elo = elos[index]
            else:
                tournies.append(
                    MonthMatches(
                        year=match.datetime.year,
                        month=match.datetime.month,
                        matches=[match],
                        last_elo=elos[index],
                    )
                )
    return tournies


class Round(BaseModel):
    matches: list[Match]
    played: list[PlayedMatch]
    closed: bool


class Tourny(BaseModel):
    year: int
    month: int
    rounds: list[Round]
    winner: str = Field(None)
    @field_serializer('winner')
    def serialize_winner(self, winner):
        return _get_username(winner)


def calc_tourny_scheme(
    month_matches: MonthMatches, previous_month_matches: MonthMatches
) -> Tourny:
    # get players
    players = []
    for match in previous_month_matches.matches:
        if match.winner not in players:
            players.append(match.winner)
        if match.loser not in players:
            players.append(match.loser)

    # sort them by elo
    players = sorted(players, key=previous_month_matches.last_elo.get, reverse=True)
    print(players)
    max_players = 4
    # check if there are four
    if len(players) < max_players:
        return None

    tourny_players = players[:max_players]
    import math

    first_matches = [
        Match(players=[tourny_players[-(i + 1)], tourny_players[i]])
        for i in range(int(len(tourny_players) / 2))
    ]
    first_round = Round(matches=first_matches, played=[], closed=False)
    rounds = int(math.log2(max_players))
    tourny = Tourny(
        year=month_matches.year,
        month=month_matches.month,
        rounds=[Round(matches=[], played=[], closed=False) for i in range(rounds)],
    )
    tourny.rounds[0] = first_round

    tourny = play_tourny(
        tourny, first_round, matches=month_matches.matches, last_match_index=0
    )
    return tourny


def make_counterparts(round: Round):
    if len(round.matches) > 1:
        for index, match in enumerate(round.matches):
            if index % 2 == 0:
                # make counterparts
                match.counterpart = round.matches[index + 1]
                round.matches[index + 1].counterpart = match
    return round


def play_tourny(
    tourny: Tourny, round: Round, matches: list[PlayedMatch], last_match_index=0
) -> Tourny:
    next_round = (
        tourny.rounds[tourny.rounds.index(round) + 1]
        if tourny.rounds.index(round) < len(tourny.rounds) - 1
        else None
    )
    round = make_counterparts(round)
    print(len(round.matches))
    for match in round.matches:
        # check if it's already played by going through the list of matches
        for index, played_match in enumerate(matches, start=last_match_index):
            if (
                played_match.winner in match.players
                and played_match.loser in match.players
            ):
                # note when the last match was played
                if index > last_match_index:
                    last_match_index = index

                # match has been played!
                round.played.append(played_match)
                match.played_match = played_match
                if not match.counterpart:
                    # this was the final!
                    round.closed = True
                    print("tourny completed!")
                    print(_get_username(played_match.winner))
                    tourny.winner = played_match.winner
                    return tourny
                else:
                    if match.counterpart.played_match:
                        # the match and its counterpart have been played. Schedule a new match!
                        if next_round:
                            print("appending next match")
                            next_round.matches.append(
                                Match(
                                    players=[
                                        played_match.winner,
                                        match.counterpart.played_match.winner,
                                    ]
                                )
                            )
                        else:
                            raise ValueError("Why does this match have a counterpart?")
                    break

    # check if all the matches have been played
    if all([match.played_match is not None for match in round.matches]):
        # round done!
        round.closed = True
        # play the next round
        return play_tourny(
            tourny=tourny,
            round=next_round,
            matches=matches,
            last_match_index=last_match_index,
        )

    else:
        print("not all matches have been played in round")
        if next_round:  # make sure the next round has counterparts
            make_counterparts(next_round)
        return tourny


@https_fn.on_call(region="europe-west1")
def get_tournies(req: https_fn.CallableRequest):
    matches = _get_matches()
    elos = _get_elo_history()
    print(len(matches))
    print(len(elos))
    monthly_matches = _calc_monthly_matches(matches, elos)
    print(len(monthly_matches))
    tournies = []
    for index, month in enumerate(monthly_matches):
        if index > 0:
            tourny = calc_tourny_scheme(
                month, previous_month_matches=monthly_matches[index - 1]
            )
            print(
                [
                    _get_username(player)
                    for round in tourny.rounds
                    for match in round.matches
                    for player in match.players
                ]
            )
            tournies.append(
                tourny.model_dump()
            )

    return tournies
