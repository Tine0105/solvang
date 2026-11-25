/* Trình vẽ biểu đồ Canvas nội bộ (tự động kích hoạt nếu CDN Chart.js không tải được khi offline) */
(function () {
  function drawBarChart(canvas, labels, values, colors) {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(rect.width || 480, 320);
    const height = Math.max(rect.height || 260, 240);
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);

    const pad = { top: 24, right: 20, bottom: 52, left: 44 };
    const plotW = width - pad.left - pad.right;
    const plotH = height - pad.top - pad.bottom;
    const maxVal = Math.max(...values, 1);

    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.fillStyle = "#9ca3af";
    ctx.font = "12px system-ui, sans-serif";
    for (let i = 0; i <= 4; i++) {
      const y = pad.top + plotH - (plotH * i) / 4;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(width - pad.right, y);
      ctx.stroke();
      ctx.fillText(String(Math.round((maxVal * i) / 4)), 10, y + 4);
    }

    const step = plotW / Math.max(labels.length, 1);
    const barW = Math.min(42, step * 0.58);
    labels.forEach((lbl, idx) => {
      const val = values[idx] || 0;
      const h = (val / maxVal) * plotH;
      const x = pad.left + idx * step + (step - barW) / 2;
      const y = pad.top + plotH - h;
      ctx.fillStyle = colors[idx % colors.length];
      ctx.beginPath();
      ctx.roundRect(x, y, barW, Math.max(h, 3), 5);
      ctx.fill();

      ctx.fillStyle = "#f3f4f6";
      ctx.textAlign = "center";
      ctx.fillText(String(val), x + barW / 2, y - 6);
      ctx.fillStyle = "#9ca3af";
      ctx.fillText(lbl.length > 10 ? lbl.slice(0, 9) + "…" : lbl, x + barW / 2, height - 22);
    });
  }

  function drawDoughnutChart(canvas, labels, values, colors) {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(rect.width || 380, 300);
    const height = Math.max(rect.height || 260, 240);
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);

    const total = values.reduce((a, b) => a + b, 0) || 1;
    const cx = width * 0.36;
    const cy = height * 0.5;
    const outerR = Math.min(cx - 20, cy - 24, 88);
    const innerR = outerR * 0.56;

    let angle = -Math.PI / 2;
    values.forEach((v, i) => {
      const slice = (v / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, outerR, angle, angle + slice);
      ctx.closePath();
      ctx.fillStyle = colors[i % colors.length];
      ctx.fill();
      angle += slice;
    });

    ctx.beginPath();
    ctx.arc(cx, cy, innerR, 0, Math.PI * 2);
    ctx.fillStyle = "#151923";
    ctx.fill();

    ctx.fillStyle = "#f3f4f6";
    ctx.font = "bold 16px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(String(values.reduce((a, b) => a + b, 0)), cx, cy + 6);

    ctx.textAlign = "left";
    ctx.font = "13px system-ui, sans-serif";
    labels.forEach((lbl, i) => {
      const ly = 44 + i * 32;
      const lx = width * 0.66;
      ctx.fillStyle = colors[i % colors.length];
      ctx.fillRect(lx, ly - 10, 12, 12);
      ctx.fillStyle = "#e5e7eb";
      ctx.fillText(`${lbl}: ${values[i]}`, lx + 20, ly);
    });
  }

  window.renderLuxCharts = function (brandData, orderData) {
    const palette = ["#d4af37", "#38bdf8", "#34d399", "#f43f5e", "#a78bfa", "#fb923c", "#60a5fa", "#facc15"];
    const statusPalette = ["#f59e0b", "#10b981", "#38bdf8", "#ef4444"];
    const brandCanvas = document.getElementById("brandChart");
    const orderCanvas = document.getElementById("orderChart");

    if (window.Chart) {
      if (brandCanvas) {
        new window.Chart(brandCanvas, {
          type: "bar",
          data: {
            labels: brandData.labels,
            datasets: [{ label: "Số mẫu xe", data: brandData.values, backgroundColor: palette, borderRadius: 6 }]
          },
          options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1, color: "#9ca3af" } }, x: { ticks: { color: "#9ca3af" } } } }
        });
      }
      if (orderCanvas) {
        new window.Chart(orderCanvas, {
          type: "doughnut",
          data: {
            labels: orderData.labels,
            datasets: [{ data: orderData.values, backgroundColor: statusPalette, borderWidth: 0 }]
          },
          options: { plugins: { legend: { labels: { color: "#e5e7eb" } } } }
        });
      }
    } else {
      if (brandCanvas) drawBarChart(brandCanvas, brandData.labels, brandData.values, palette);
      if (orderCanvas) drawDoughnutChart(orderCanvas, orderData.labels, orderData.values, statusPalette);
    }
  };
})();
