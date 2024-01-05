# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app
from firebase_admin import storage, db
initialize_app()
user_ref = db.reference("users")
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
        user_ref.set( {req.auth.uid:{"name": req.data["username"]}})
    return req.auth.uid, user_ref.child(req.auth.uid).get()

