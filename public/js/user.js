const loader = new Loader($("#container"))
document.addEventListener('DOMContentLoaded', function () {
    createUserAccount = firebase.functions().httpsCallable('create_user_account');
        firebase.auth().onAuthStateChanged(function (loadedUser) {
            loader.stopLoader()
            if (loadedUser) {
                console.log(loadedUser);
                createUserAccount({"username": loadedUser.displayName});
                $("#username").text(loadedUser.displayName)
            } 
        })
});
