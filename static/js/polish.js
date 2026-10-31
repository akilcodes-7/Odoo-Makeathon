(() => {
  "use strict";
  // Everything here is optional: the server already renders the final numbers and tables.
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const formatRupees = (paise) => {
    const rupees = (paise / 100).toFixed(2).split(".");
    const digits = rupees[0];
    const head = digits.slice(0, -3);
    const firstGroupSize = head.length % 2 || 2;
    const groupedHead = head.length > firstGroupSize
      ? head.slice(0, firstGroupSize) + "," + head.slice(firstGroupSize).match(/.{2}/g).join(",")
      : head;
    const grouped = digits.length > 3
      ? groupedHead + "," + digits.slice(-3)
      : digits;
    return `₹${grouped}.${rupees[1]}`;
  };

  // 1) Count-up for KPI numbers: <strong data-count-paise="370000">₹3,700.00</strong> or data-count="2"
  document.querySelectorAll("[data-count-paise], [data-count]").forEach((el) => {
    const isMoney = el.hasAttribute("data-count-paise");
    const end = Number(isMoney ? el.dataset.countPaise : el.dataset.count);
    if (!Number.isFinite(end) || end <= 0 || reduced) return;
    const finalText = el.textContent;
    const fmt = (n) => isMoney ? formatRupees(n) : String(Math.round(n));
    const start = performance.now();
    const duration = 700;
    const tick = (now) => {
      const p = Math.min((now - start) / duration, 1);
      el.textContent = fmt(end * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(tick); else el.textContent = finalText; // end on the server's exact text
    };
    requestAnimationFrame(tick);
  });

  // 2) Bar chart for "Collections by day", built from the table so the data stays accessible
  const table = document.querySelector("[data-collections-table]");
  if (table) {
    const rows = [...table.querySelectorAll("tbody tr")]
      .map((tr) => ({ day: tr.cells[0]?.textContent.trim(), paise: Number(tr.cells[2]?.dataset.amount) }))
      .filter((r) => Number.isFinite(r.paise));
    const max = Math.max(...rows.map((r) => r.paise), 0);
    if (rows.length >= 2 && max > 0) {
      const chart = document.createElement("div");
      chart.className = "collections-chart no-print";
      chart.setAttribute("aria-hidden", "true"); // the table below carries the same data for screen readers
      rows.forEach((r, i) => {
        const bar = document.createElement("span");
        bar.className = "bar";
        bar.style.setProperty("--h", Math.max((r.paise / max) * 100, 4) + "%");
        bar.style.setProperty("--i", i);
        bar.dataset.tip = `${r.day}: ${formatRupees(r.paise)}`;
        chart.appendChild(bar);
      });
      (table.closest(".table-scroll") || table).before(chart);
    }
  }
})();
