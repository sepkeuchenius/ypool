
document.addEventListener('DOMContentLoaded', function () {
    const getScore = firebase.functions().httpsCallable('get_score');
    firebase.functions().useEmulator("localhost", 5001);
    firebase.auth().onAuthStateChanged(function (loadedUser) {
        if (loadedUser) {
            getScore().then(function (matches) {
                for (_match of matches.data){
                    $("#score-table").append(`<tr><td>${_match.winner}</td><td>${_match.loser}</td><td>${_match.issuer}</td>`)
                }
            });
            
        } 
    })
});
