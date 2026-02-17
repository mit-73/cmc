// ══════════════════════════════════════════
// Chart creation helpers (Chart.js wrappers)
// ══════════════════════════════════════════

var chartColors = {
  line: '#58a6ff', fill: 'rgba(88,166,255,0.1)',
  bar: 'rgba(88,166,255,0.7)', barBorder: '#58a6ff',
  grid: 'rgba(48,54,61,0.5)', tick: '#8b949e',
};

function createBarChart(canvasId, labels, data, label, dir, pctLabels) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return;
  var horizontal = dir === 'horizontal';
  var cfg = {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: label, data: data,
        backgroundColor: chartColors.bar, borderColor: chartColors.barBorder, borderWidth: 1,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      indexAxis: horizontal ? 'y' : 'x',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              var v = ctx.parsed[horizontal ? 'x' : 'y'];
              var pct = pctLabels ? pctLabels[ctx.dataIndex] : '';
              return label + ': ' + v.toLocaleString() + (pct ? ' (' + pct + ')' : '');
            },
          },
        },
      },
      scales: {
        x: { grid: { color: chartColors.grid }, ticks: { color: chartColors.tick, maxRotation: 45 } },
        y: { grid: { color: chartColors.grid }, ticks: { color: chartColors.tick }, beginAtZero: true },
      },
    },
  };
  if (horizontal) {
    canvas.style.height = Math.max(200, labels.length * 28) + 'px';
    canvas.parentElement.style.height = canvas.style.height;
  }
  var c = new Chart(canvas, cfg);
  chartInstances.push(c);
  return c;
}

function createLineChart(canvasId, labels, data, label) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return;
  var c = new Chart(canvas, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: label, data: data,
        borderColor: chartColors.line, backgroundColor: chartColors.fill,
        fill: true, tension: 0.3, pointRadius: 4, pointBackgroundColor: chartColors.line,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: true, labels: { color: chartColors.tick } } },
      scales: {
        x: { grid: { color: chartColors.grid }, ticks: { color: chartColors.tick, maxRotation: 45 } },
        y: { grid: { color: chartColors.grid }, ticks: { color: chartColors.tick }, beginAtZero: true },
      },
    },
  });
  chartInstances.push(c);
  return c;
}

function createGroupedBarChart(canvasId, labels, dataA, dataB, labelA, labelB) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return;
  var c = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        { label: labelA, data: dataA, backgroundColor: 'rgba(139,148,158,0.5)', borderColor: '#8b949e', borderWidth: 1 },
        { label: labelB, data: dataB, backgroundColor: 'rgba(88,166,255,0.7)', borderColor: '#58a6ff', borderWidth: 1 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: true, labels: { color: chartColors.tick } } },
      scales: {
        x: { grid: { color: chartColors.grid }, ticks: { color: chartColors.tick } },
        y: { grid: { color: chartColors.grid }, ticks: { color: chartColors.tick }, beginAtZero: true },
      },
    },
  });
  chartInstances.push(c);
}
