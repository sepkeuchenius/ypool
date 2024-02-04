var userExists;
var createUser;
var login
const loader = new Loader($("#login-form"))
document.addEventListener('DOMContentLoaded', function () {
    userExists = functions.httpsCallable('user_exists');
    createUser = functions.httpsCallable('create_user');
    window.setTimeout(() => {
        firebase.auth().onAuthStateChanged(async function (loadedUser) {
            loader.stopLoader()
            if (loadedUser) {
                await requestNotificationPermission()
                window.location.replace("/score")
            }
            else {
                await getNotificationToken();
            }
        })

    })
})

function enteredEmail() {
    userExists({ "email": $("#email").val() }).then((res) => {
        if (!res.data) {
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
            .catch((err) => { 
                $("#wrong-password").show();
                $("#reset-password").show()
            })
        }
        else {
            createUser({ "email": $("#email").val(), "password": $("#password").val(), "display_name": $("#display-name").val() }).then((res) => {
                if (res.data) {
                    firebase.auth().signInWithEmailAndPassword($("#email").val(), $("#password").val())
                }
            })
        }
    })
}

function signOut() {
    firebase.auth().signOut();
}


function resetPassword(){
    firebase.auth().sendPasswordResetEmail($("#email").val()).then((res)=>{
        $("#reset-sent").show();
    }).catch((err)=>{
        $("#reset-failed").show();
    });
}