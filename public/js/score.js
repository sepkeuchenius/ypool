const match_loader = new Loader($("#match-table"))
const score_loader = new Loader($("#score-table"))
const bar_loader = new Loader($("#bar-container"))
var getElos;
var getBarChart;
var getMostEfficientOpponent;
var subscribeToPoolNotifications;
var generateText;
document.addEventListener('DOMContentLoaded', function () {
    const getScore = functions.httpsCallable('get_score');
    getElos = functions.httpsCallable('get_elo_ratings');
    getBarChart = functions.httpsCallable('get_bar_chart');
    getMostEfficientOpponent = functions.httpsCallable('get_most_efficient_opponent');
    subscribeToPoolNotifications = functions.httpsCallable('subscribe_to_pool');
    generateText = functions.httpsCallable('generate_text');
    firebase.auth().onAuthStateChanged(async function (loadedUser) {
        if (loadedUser) {
            await requestNotificationPermission();
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
                console.log(res)
                for (score_i in res.data.ranking) {
                    const [name, elo] = res.data.ranking[score_i]
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
                var datasets = [];
                for (player in res.data.history) {
                    datasets.push({
                        "label": player, "data": res.data.history[player], fill: false,
                        tension: 0.1
                    })
                }
                const data = {
                    labels: datasets[0]['data'].map((val, index) => { return index }),
                    datasets: datasets,
                };
                const config = {
                    type: 'line',
                    data: data,
                    options: {
                        maintainAspectRatio: false,
                        elements: {
                            point: {
                                radius: 0
                            }
                        }
                    }
                };
                new Chart($("#line"), config)


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
        else {
            window.location.replace("/")
        }
    })
});
