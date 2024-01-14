var userExists;
var createUser;
var login
const loader = new Loader($("#login-form"))
document.addEventListener('DOMContentLoaded', function () {
    userExists = firebase.functions().httpsCallable('user_exists');
    createUser = firebase.functions().httpsCallable('create_user');
    window.setTimeout(() => {
        firebase.auth().onAuthStateChanged(function (loadedUser) {
            loader.stopLoader()
            if (loadedUser) {
                window.location.replace("/score")
                // loadUser({"user": loadedUser})
            } 
        })

    })
})

function enteredEmail() {
    userExists({ "email": $("#email").val() }).then((res) => {
        if (!res.data) {
            //enter password
            $("#display-name").show();
            $("#login-button").text("Create Account")
        }
        $("#password").show();
        $("#login-button").show()
        $("#next").hide()
    })
}
function createUserOrLogin() {
    userExists({ "email": $("#email").val() }).then((res) => {
        if (res.data) {
            //account exists
            firebase.auth().signInWithEmailAndPassword($("#email").val(), $("#password").val())
        }
        else {
            createUser({ "email": $("#email").val(), "password": $("#password").val(), "display_name": $("#display-name").val() }).then((res)=>{
                if(res.data){
                    firebase.auth().signInWithEmailAndPassword($("#email").val(), $("#password").val())
                }
            })
        }
    })
}

function signOut(){
    firebase.auth().signOut();
}