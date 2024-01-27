const match_loader = new Loader($("#match-table"))
const score_loader = new Loader($("#score-table"))
const bar_loader = new Loader($("#bar-container"))
var getElos;
var getBarChart;
var getMostEfficientOpponent;
var subscribeToPoolNotifications;
document.addEventListener('DOMContentLoaded', function () {
    const getScore = firebase.functions().httpsCallable('get_score');
    getElos = firebase.functions().httpsCallable('get_elo_ratings');
    getBarChart = firebase.functions().httpsCallable('get_bar_chart');
    getMostEfficientOpponent = firebase.functions().httpsCallable('get_most_efficient_opponent');
    subscribeToPoolNotifications = firebase.functions().httpsCallable('subscribe_to_pool');
    firebase.auth().onAuthStateChanged(function (loadedUser) {
        if (loadedUser) {
            getScore().then(function (matches) {
                for (_match of matches.data) {
                    $("#match-table").append(`<tr><td>${_match.winner}</td><td>${_match.loser}</td><td>${_match.issuer}</td>`)
                }
                $("#match-table td, #score-table td").each(function (el) {
                    if ($(this).text().includes(loadedUser.displayName)) {
                        $(this).css("color", "var(--blue)")
                    }
                })
                match_loader.stopLoader()
            });
            getElos().then(function (res) {
                for (score_i in res.data) {
                    const [name, elo] = res.data[score_i]
                    var place = Number(score_i) + 1;
                    if (place == 1) {
                        place = "&#129351;"
                    }
                    else if (place == 2) {
                        place = "&#129352;"
                    }
                    else if (place == 3) {
                        place = "&#129353;"
                    }
                    $("#score-table").append(`<tr><td>${place}</td><td>${name}</td><td>${Number(elo).toFixed(2)}</td>`)
                }

                $("#match-table td, #score-table td").each(function (el) {
                    if ($(this).text().includes(loadedUser.displayName)) {
                        $(this).css("color", "var(--blue)")
                    }
                })
                score_loader.stopLoader()
            })
            getBarChart().then((res) => {
                const data = {
                    labels: res.data.labels,
                    datasets: res.data.sets,
                };
                const config = {
                    type: 'bar',
                    data: data,
                    options: {
                        plugins: {
                            title: {
                                display: true,
                                text: 'Stats'
                            },
                        },
                        // responsive: true,    
                        interaction: {
                            intersect: false,
                        },
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                stacked: true,
                            },
                            y: {
                                stacked: true
                            }
                        }
                    }
                };
                const ctx = $("#bar")
                new Chart(ctx, config)
                bar_loader.stopLoader()
            })
            getMostEfficientOpponent().then((res) => {
                console.log(res)
                $("#most-efficient-opponent").text(res.data.most_efficient_opponent)
                $("#potential-elo").text(res.data.potential_elo.toFixed(2))
                $("#potential-place").text(res.data.potential_place.toFixed(0))
                $("#play-hint").show()
            })

        }
    })
});




function getToken() {
    const messaging = firebase.messaging();
    // [START messaging_get_token]
    // Get registration token. Initially this makes a network call, once retrieved
    // subsequent calls to getToken will return from cache.
    messaging.getToken({ vapidKey: 'BMe2ouKwxdv2lZn23AO95IuEC1UKj7Pr03pbDPaOOF66sEqEyie_slj7MDkWdldXb4NaZJZBeEbEE0KqiNiul-o' }).then((currentToken) => {
        if (currentToken) {
            // Send the token to your server and update the UI if necessary
            // ...
            console.log(currentToken)
            subscribeToPoolNotifications({"tokens": [currentToken]}).then((res)=>{
                console.log(res.data)
            })
        } else {
            // Show permission request UI
            console.log('No registration token available. Request permission to generate one.');
            // ...
        }
    }).catch((err) => {
        console.log('An error occurred while retrieving token. ', err);
        // ...
    });
    // [END messaging_get_token]
}