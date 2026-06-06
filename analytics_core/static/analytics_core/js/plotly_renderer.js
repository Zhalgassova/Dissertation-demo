(function () {
    const script = document.getElementById("plotly-charts");
    if (!script || typeof Plotly === "undefined") {
        return;
    }

    const charts = JSON.parse(script.textContent || "[]");
    charts.forEach(function (chart, index) {
        const target = document.getElementById(chart.dom_id || ("chart-" + (index + 1)));
        if (!target || !chart.figure) {
            return;
        }
        Plotly.newPlot(target, chart.figure.data || [], chart.figure.layout || {}, {
            responsive: true,
            displaylogo: false,
            modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d"],
        });
    });
})();
