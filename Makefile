SHELL=/bin/bash

install-requirements:
	curl -sL https://firebase.tools | bash
	firebase login

develop:
	firebase emulators:start  --import=./db

yeet:
	firebase deploy
