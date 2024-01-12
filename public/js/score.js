var getElos;
document.addEventListener('DOMContentLoaded', function () {
    const getScore = firebase.functions().httpsCallable('get_score');
    getElos = firebase.functions().httpsCallable('get_elo_ratings');
    firebase.auth().onAuthStateChanged(function (loadedUser) {
        if (loadedUser) {
            getScore().then(function (matches) {
                for (_match of matches.data){
                    $("#match-table").append(`<tr><td>${_match.winner}</td><td>${_match.loser}</td><td>${_match.issuer}</td>`)
                }
            });
            getElos().then(function(res){
                for(score_i in res.data){
                    const score = res.data[score_i]
                    $("#score-table").append(`<tr><td>${Number(score_i) + 1} ${score[0]}</td><td>${Number(score[1]).toFixed(2)}</td>`)
                }
            })
            
        } 
    })
});
