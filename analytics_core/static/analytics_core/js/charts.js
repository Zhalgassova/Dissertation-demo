(function () {
    const script = document.getElementById("charts-data");
    if (!script) {
        return;
    }

    const charts = JSON.parse(script.textContent || "[]");
    const palette = ["#186f65", "#d38b5d", "#7d8f69", "#c55a3c", "#5b7c99", "#b38d4d"];

    function svgEl(name, attrs = {}) {
        const node = document.createElementNS("http://www.w3.org/2000/svg", name);
        Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
        return node;
    }

    function clear(node) {
        while (node.firstChild) {
            node.removeChild(node.firstChild);
        }
    }

    function renderNoData(container) {
        container.innerHTML = '<div class="chart-empty">����� ��������</div>';
    }

    function shorten(label, size = 14) {
        const text = String(label || "");
        return text.length > size ? `${text.slice(0, size)}�` : text;
    }

    function renderBar(container, chart, horizontal = false) {
        const labels = chart.labels || [];
        const values = chart.values || [];
        if (!labels.length || !values.length) {
            renderNoData(container);
            return;
        }

        const width = 560;
        const height = 300;
        const padding = { top: 20, right: 20, bottom: horizontal ? 20 : 56, left: horizontal ? 120 : 38 };
        const plotWidth = width - padding.left - padding.right;
        const plotHeight = height - padding.top - padding.bottom;
        const maxValue = Math.max(...values, 1);
        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart-svg" });

        svg.appendChild(svgEl("line", {
            x1: padding.left,
            y1: padding.top + plotHeight,
            x2: padding.left + plotWidth,
            y2: padding.top + plotHeight,
            class: "axis-line",
        }));

        if (horizontal) {
            const barHeight = plotHeight / labels.length - 8;
            labels.forEach((label, index) => {
                const value = values[index];
                const barWidth = (value / maxValue) * plotWidth;
                const y = padding.top + index * (barHeight + 8);
                svg.appendChild(svgEl("text", {
                    x: 10,
                    y: y + barHeight / 2 + 4,
                    class: "axis-label",
                })).textContent = shorten(label, 18);
                svg.appendChild(svgEl("rect", {
                    x: padding.left,
                    y,
                    width: barWidth,
                    height: barHeight,
                    rx: 8,
                    fill: palette[index % palette.length],
                }));
                svg.appendChild(svgEl("text", {
                    x: padding.left + barWidth + 8,
                    y: y + barHeight / 2 + 4,
                    class: "value-label",
                })).textContent = value;
            });
        } else {
            const barWidth = plotWidth / labels.length - 10;
            labels.forEach((label, index) => {
                const value = values[index];
                const x = padding.left + index * (barWidth + 10);
                const barHeight = (value / maxValue) * plotHeight;
                const y = padding.top + plotHeight - barHeight;
                svg.appendChild(svgEl("rect", {
                    x,
                    y,
                    width: barWidth,
                    height: barHeight,
                    rx: 8,
                    fill: palette[index % palette.length],
                }));
                svg.appendChild(svgEl("text", {
                    x: x + barWidth / 2,
                    y: y - 6,
                    class: "value-label centered",
                })).textContent = value;
                svg.appendChild(svgEl("text", {
                    x: x + barWidth / 2,
                    y: height - 18,
                    class: "axis-label centered",
                })).textContent = shorten(label, 10);
            });
        }

        clear(container);
        container.appendChild(svg);
    }

    function renderLine(container, chart) {
        const labels = chart.labels || [];
        const values = chart.values || [];
        if (!labels.length || !values.length) {
            renderNoData(container);
            return;
        }
        const width = 560;
        const height = 300;
        const padding = { top: 20, right: 18, bottom: 52, left: 40 };
        const plotWidth = width - padding.left - padding.right;
        const plotHeight = height - padding.top - padding.bottom;
        const minValue = Math.min(...values, 0);
        const maxValue = Math.max(...values, 100);
        const range = Math.max(maxValue - minValue, 1);
        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart-svg" });
        const points = values.map((value, index) => {
            const x = padding.left + (index / Math.max(labels.length - 1, 1)) * plotWidth;
            const y = padding.top + plotHeight - ((value - minValue) / range) * plotHeight;
            return `${x},${y}`;
        }).join(" ");

        svg.appendChild(svgEl("polyline", {
            points,
            fill: "none",
            stroke: "#186f65",
            "stroke-width": 3,
            "stroke-linejoin": "round",
            "stroke-linecap": "round",
        }));

        values.forEach((value, index) => {
            const x = padding.left + (index / Math.max(labels.length - 1, 1)) * plotWidth;
            const y = padding.top + plotHeight - ((value - minValue) / range) * plotHeight;
            svg.appendChild(svgEl("circle", { cx: x, cy: y, r: 4, fill: "#c55a3c" }));
            svg.appendChild(svgEl("text", {
                x,
                y: y - 10,
                class: "value-label centered",
            })).textContent = value;
            svg.appendChild(svgEl("text", {
                x,
                y: height - 18,
                class: "axis-label centered",
            })).textContent = shorten(labels[index], 10);
        });

        clear(container);
        container.appendChild(svg);
    }

    function polarToCartesian(cx, cy, radius, angle) {
        const radians = (angle - 90) * Math.PI / 180;
        return {
            x: cx + radius * Math.cos(radians),
            y: cy + radius * Math.sin(radians),
        };
    }

    function describeArc(cx, cy, radius, startAngle, endAngle) {
        const start = polarToCartesian(cx, cy, radius, endAngle);
        const end = polarToCartesian(cx, cy, radius, startAngle);
        const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
        return [
            "M", start.x, start.y,
            "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y,
        ].join(" ");
    }

    function renderDoughnut(container, chart) {
        const labels = chart.labels || [];
        const values = chart.values || [];
        if (!labels.length || !values.length) {
            renderNoData(container);
            return;
        }
        const width = 560;
        const height = 300;
        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart-svg" });
        const total = values.reduce((sum, value) => sum + value, 0) || 1;
        let angle = 0;
        values.forEach((value, index) => {
            const sliceAngle = (value / total) * 360;
            const path = svgEl("path", {
                d: describeArc(140, 150, 90, angle, angle + sliceAngle),
                fill: "none",
                stroke: palette[index % palette.length],
                "stroke-width": 42,
            });
            svg.appendChild(path);
            angle += sliceAngle;
        });
        svg.appendChild(svgEl("text", {
            x: 140,
            y: 146,
            class: "value-label centered big",
        })).textContent = total;
        svg.appendChild(svgEl("text", {
            x: 140,
            y: 168,
            class: "axis-label centered",
        })).textContent = "�����? �����";

        labels.forEach((label, index) => {
            const y = 76 + index * 34;
            svg.appendChild(svgEl("rect", {
                x: 300,
                y: y - 11,
                width: 14,
                height: 14,
                rx: 4,
                fill: palette[index % palette.length],
            }));
            svg.appendChild(svgEl("text", {
                x: 324,
                y,
                class: "axis-label",
            })).textContent = `${label}: ${values[index]}`;
        });

        clear(container);
        container.appendChild(svg);
    }

    function renderScatter(container, chart) {
        const points = chart.points || [];
        if (!points.length) {
            renderNoData(container);
            return;
        }
        const width = 560;
        const height = 300;
        const padding = { top: 16, right: 16, bottom: 46, left: 40 };
        const plotWidth = width - padding.left - padding.right;
        const plotHeight = height - padding.top - padding.bottom;
        const xValues = points.map((item) => item.x);
        const yValues = points.map((item) => item.y);
        const minX = Math.min(...xValues, 0);
        const maxX = Math.max(...xValues, 100);
        const minY = Math.min(...yValues, 0);
        const maxY = Math.max(...yValues, 1);
        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart-svg" });

        svg.appendChild(svgEl("line", {
            x1: padding.left,
            y1: padding.top + plotHeight,
            x2: padding.left + plotWidth,
            y2: padding.top + plotHeight,
            class: "axis-line",
        }));
        svg.appendChild(svgEl("line", {
            x1: padding.left,
            y1: padding.top,
            x2: padding.left,
            y2: padding.top + plotHeight,
            class: "axis-line",
        }));

        points.forEach((point, index) => {
            const x = padding.left + ((point.x - minX) / Math.max(maxX - minX, 1)) * plotWidth;
            const y = padding.top + plotHeight - ((point.y - minY) / Math.max(maxY - minY, 1)) * plotHeight;
            svg.appendChild(svgEl("circle", {
                cx: x,
                cy: y,
                r: 5,
                fill: palette[index % palette.length],
                opacity: 0.85,
            }));
            svg.appendChild(svgEl("text", {
                x: x + 8,
                y: y - 8,
                class: "axis-label",
            })).textContent = shorten(point.label, 12);
        });

        clear(container);
        container.appendChild(svg);
    }

    function renderHeatmap(container, chart) {
        const xLabels = chart.xLabels || [];
        const yLabels = chart.yLabels || [];
        const matrix = chart.matrix || [];
        if (!xLabels.length || !yLabels.length || !matrix.length) {
            renderNoData(container);
            return;
        }
        const width = 560;
        const height = 320;
        const padding = { top: 40, right: 10, bottom: 30, left: 96 };
        const plotWidth = width - padding.left - padding.right;
        const plotHeight = height - padding.top - padding.bottom;
        const cellWidth = plotWidth / xLabels.length;
        const cellHeight = plotHeight / yLabels.length;
        const flat = matrix.flat();
        const minValue = Math.min(...flat, 0);
        const maxValue = Math.max(...flat, 100);
        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart-svg" });

        function colorFor(value) {
            const ratio = (value - minValue) / Math.max(maxValue - minValue, 1);
            const hue = 10 + ratio * 130;
            return `hsl(${hue}, 55%, ${82 - ratio * 38}%)`;
        }

        yLabels.forEach((rowLabel, rowIndex) => {
            svg.appendChild(svgEl("text", {
                x: 8,
                y: padding.top + rowIndex * cellHeight + cellHeight / 2 + 4,
                class: "axis-label",
            })).textContent = shorten(rowLabel, 14);
            xLabels.forEach((colLabel, colIndex) => {
                const value = matrix[rowIndex][colIndex];
                const x = padding.left + colIndex * cellWidth;
                const y = padding.top + rowIndex * cellHeight;
                svg.appendChild(svgEl("rect", {
                    x,
                    y,
                    width: cellWidth - 4,
                    height: cellHeight - 4,
                    rx: 8,
                    fill: colorFor(value),
                }));
                svg.appendChild(svgEl("text", {
                    x: x + cellWidth / 2,
                    y: y + cellHeight / 2 + 4,
                    class: "value-label centered",
                })).textContent = value;
                if (rowIndex === 0) {
                    svg.appendChild(svgEl("text", {
                        x: x + cellWidth / 2,
                        y: 22,
                        class: "axis-label centered",
                    })).textContent = shorten(colLabel, 10);
                }
            });
        });

        clear(container);
        container.appendChild(svg);
    }

    function renderStackedBar(container, chart) {
        const labels = chart.labels || [];
        const series = chart.series || [];
        if (!labels.length || !series.length) {
            renderNoData(container);
            return;
        }
        const width = 560;
        const height = 300;
        const padding = { top: 20, right: 18, bottom: 48, left: 38 };
        const plotWidth = width - padding.left - padding.right;
        const plotHeight = height - padding.top - padding.bottom;
        const totals = labels.map((_, index) => series.reduce((sum, item) => sum + (item.values[index] || 0), 0));
        const maxValue = Math.max(...totals, 1);
        const barWidth = plotWidth / labels.length - 12;
        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart-svg" });

        labels.forEach((label, index) => {
            let currentY = padding.top + plotHeight;
            series.forEach((item, seriesIndex) => {
                const value = item.values[index] || 0;
                const segmentHeight = (value / maxValue) * plotHeight;
                currentY -= segmentHeight;
                svg.appendChild(svgEl("rect", {
                    x: padding.left + index * (barWidth + 12),
                    y: currentY,
                    width: barWidth,
                    height: segmentHeight,
                    rx: 8,
                    fill: palette[seriesIndex % palette.length],
                }));
            });
            svg.appendChild(svgEl("text", {
                x: padding.left + index * (barWidth + 12) + barWidth / 2,
                y: height - 18,
                class: "axis-label centered",
            })).textContent = shorten(label, 10);
        });

        series.forEach((item, index) => {
            const y = 18 + index * 18;
            svg.appendChild(svgEl("rect", { x: 370, y: y - 10, width: 12, height: 12, rx: 4, fill: palette[index % palette.length] }));
            svg.appendChild(svgEl("text", { x: 390, y, class: "axis-label" })).textContent = item.name;
        });

        clear(container);
        container.appendChild(svg);
    }

    function renderMultiBar(container, chart) {
        const labels = chart.labels || [];
        const series = chart.series || [];
        if (!labels.length || !series.length) {
            renderNoData(container);
            return;
        }
        const width = 560;
        const height = 300;
        const padding = { top: 20, right: 18, bottom: 48, left: 38 };
        const plotWidth = width - padding.left - padding.right;
        const plotHeight = height - padding.top - padding.bottom;
        const values = series.flatMap((item) => item.values || []);
        const maxValue = Math.max(...values, 1);
        const groupWidth = plotWidth / labels.length;
        const innerBarWidth = Math.max((groupWidth - 18) / series.length, 16);
        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart-svg" });

        labels.forEach((label, labelIndex) => {
            const groupStart = padding.left + labelIndex * groupWidth + 8;
            series.forEach((item, seriesIndex) => {
                const value = item.values[labelIndex] || 0;
                const barHeight = (value / maxValue) * plotHeight;
                const x = groupStart + seriesIndex * innerBarWidth;
                const y = padding.top + plotHeight - barHeight;
                svg.appendChild(svgEl("rect", {
                    x,
                    y,
                    width: innerBarWidth - 4,
                    height: barHeight,
                    rx: 8,
                    fill: palette[seriesIndex % palette.length],
                }));
                svg.appendChild(svgEl("text", {
                    x: x + (innerBarWidth - 4) / 2,
                    y: y - 6,
                    class: "value-label centered",
                })).textContent = value;
            });
            svg.appendChild(svgEl("text", {
                x: groupStart + (series.length * innerBarWidth) / 2,
                y: height - 18,
                class: "axis-label centered",
            })).textContent = shorten(label, 12);
        });

        series.forEach((item, index) => {
            const y = 18 + index * 18;
            svg.appendChild(svgEl("rect", { x: 370, y: y - 10, width: 12, height: 12, rx: 4, fill: palette[index % palette.length] }));
            svg.appendChild(svgEl("text", { x: 390, y, class: "axis-label" })).textContent = item.name;
        });

        clear(container);
        container.appendChild(svg);
    }

    charts.forEach((chart) => {
        const container = document.querySelector(`[data-chart-id="${chart.id}"]`);
        if (!container) {
            return;
        }
        if (chart.type === "bar") {
            renderBar(container, chart, false);
        } else if (chart.type === "hbar") {
            renderBar(container, chart, true);
        } else if (chart.type === "line") {
            renderLine(container, chart);
        } else if (chart.type === "doughnut") {
            renderDoughnut(container, chart);
        } else if (chart.type === "scatter") {
            renderScatter(container, chart);
        } else if (chart.type === "heatmap") {
            renderHeatmap(container, chart);
        } else if (chart.type === "stackedbar") {
            renderStackedBar(container, chart);
        } else if (chart.type === "multibar") {
            renderMultiBar(container, chart);
        } else {
            renderNoData(container);
        }
    });
})();
