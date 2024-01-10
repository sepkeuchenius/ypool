# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app
from firebase_admin import storage, db, auth
initialize_app()
user_ref = db.reference("users")
matches_ref = db.reference("matches")
#
#
# @https_fn.on_request()
# def on_request_example(req: https_fn.Request) -> https_fn.Response:
#     return https_fn.Response("Hello world!")

@https_fn.on_call()
def on_request_example(req:  https_fn.CallableRequest) -> https_fn.Response:
    return "Hoi"


@https_fn.on_call()
def create_user_account(req: https_fn.CallableRequest):
    print(req)
    if not user_ref.child(req.auth.uid).get():
        user_ref.update({req.auth.uid:{"name": req.data["username"]}})
    return req.auth.uid, user_ref.child(req.auth.uid).get()

@https_fn.on_call()
def get_all_users(req: https_fn.CallableRequest):
    return [{"uid": uid, "name": d["name"]} for uid, d in user_ref.get().items()]

@https_fn.on_call()
def save_match(req: https_fn.CallableRequest):
    print(req)
    winner = req.data["opponent"] if req.data["outcome"] == "lost" else req.auth.uid
    loser = req.data["opponent"] if winner == req.auth.uid else req.auth.uid 
    matches_ref.push({"winner": winner, "loser": loser, "issuer": req.auth.uid})
    return "OK"

@https_fn.on_call()
def get_score(req: https_fn.CallableRequest):
    matches = matches_ref.get().values()
    uid2names = {uid: userinfo["name"] for uid, userinfo in user_ref.get().items()}
    return [{"winner": uid2names[match["winner"]], "loser": uid2names[match["loser"]], "issuer": uid2names[match["issuer"]]} for match in matches]
    

@https_fn.on_call()
def user_exists(req: https_fn.CallableRequest):
    return  len(auth.get_users(identifiers=[auth.EmailIdentifier(req.data["email"])]).users) > 0


@https_fn.on_call()
def create_user(req: https_fn.CallableRequest):
    return  auth.create_user(email=req.data["email"], display_name=req.data["display_name"], password=req.data["password"]).uid

