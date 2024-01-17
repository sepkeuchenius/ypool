SHELL=/bin/bash

install-requirements:
	curl -sL https://firebase.tools | bash
	firebase login

develop:
	nvm use 20 || true
	firebase emulators:start  --import=./db