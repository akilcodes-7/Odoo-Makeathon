(() => {
  "use strict";
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const sidebar = document.querySelector("[data-sidebar]");
  const toggle = document.querySelector("[data-drawer-toggle]");
  const scrim = document.querySelector("[data-drawer-scrim]");
  const appMain = document.querySelector(".app-main");
  const confirmDialog = document.querySelector("[data-confirmation-dialog]");

  if (sidebar && toggle && scrim) {
    let previousFocus = null;
    const isOpen = () => sidebar.classList.contains("is-open");
    const focusable = () => [...sidebar.querySelectorAll('a[href]:not([href="#"]), button:not(:disabled), [tabindex="0"]')];
    const close = ({ restoreFocus = true } = {}) => {
      sidebar.classList.remove("is-open");
      scrim.hidden = true;
      if (appMain) appMain.inert = false;
      toggle.setAttribute("aria-expanded", "false");
      if (restoreFocus) (previousFocus || toggle).focus({ preventScroll: true });
    };
    const open = () => {
      previousFocus = document.activeElement;
      scrim.hidden = false;
      sidebar.classList.add("is-open");
      if (appMain) appMain.inert = true;
      toggle.setAttribute("aria-expanded", "true");
      const firstLink = focusable()[0];
      if (firstLink) firstLink.focus({ preventScroll: true });
    };
    toggle.addEventListener("click", () => isOpen() ? close() : open());
    scrim.addEventListener("click", () => close());
    document.addEventListener("keydown", (event) => {
      if (!isOpen()) return;
      if (event.key === "Escape") {
        event.preventDefault();
        close();
        return;
      }
      if (event.key === "Tab") {
        const items = focusable();
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault(); first.focus();
        }
      }
    });
    document.addEventListener("click", (event) => {
      if (event.target.closest("[data-sidebar] a[href]:not([href='#'])") && window.matchMedia("(max-width: 767px)").matches) {
        close({ restoreFocus: false });
      }
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 767 && isOpen()) {
        sidebar.classList.remove("is-open");
        scrim.hidden = true;
        if (appMain) appMain.inert = false;
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  document.addEventListener("click", (event) => {
    const dismiss = event.target.closest("[data-dismiss-message]");
    if (dismiss) dismiss.closest("[data-message]")?.remove();

    const trigger = event.target.closest("[data-confirm]");
    if (!trigger) return;
    if (!confirmDialog || typeof confirmDialog.showModal !== "function") {
      if (!window.confirm(trigger.dataset.confirm || "Are you sure you want to continue?")) event.preventDefault();
      return;
    }
    event.preventDefault();
    confirmDialog.dataset.message = trigger.dataset.confirm || "Are you sure you want to continue?";
    confirmDialog.dataset.title = trigger.dataset.confirmTitle || "Please confirm";
    confirmDialog.dataset.acceptLabel = trigger.dataset.confirmAccept || "Continue";
    confirmDialog.dataset.targetId = trigger.id || "";
    confirmDialog._pendingTrigger = trigger;
    confirmDialog.querySelector("#confirmation-dialog-title").textContent = confirmDialog.dataset.title;
    confirmDialog.querySelector("#confirmation-dialog-message").textContent = confirmDialog.dataset.message;
    confirmDialog.querySelector("[data-confirm-accept]").textContent = confirmDialog.dataset.acceptLabel;
    confirmDialog.showModal();
  });

  if (confirmDialog) {
    const cancel = confirmDialog.querySelector("[data-confirm-cancel]");
    const accept = confirmDialog.querySelector("[data-confirm-accept]");
    cancel?.addEventListener("click", () => confirmDialog.close("cancel"));
    confirmDialog.addEventListener("close", () => {
      const trigger = confirmDialog._pendingTrigger;
      confirmDialog._pendingTrigger = null;
      if (trigger?.isConnected) trigger.focus({ preventScroll: true });
    });
    accept?.addEventListener("click", () => {
      const trigger = confirmDialog._pendingTrigger;
      confirmDialog.close("accept");
      if (!trigger?.isConnected) return;
      if (trigger instanceof HTMLAnchorElement) {
        window.location.assign(trigger.href);
      } else if (trigger.form) {
        trigger.form.requestSubmit(trigger);
      } else {
        trigger.click();
      }
    });
  }

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!form.matches("form[data-pending-submit]") || !form.checkValidity()) return;
    const submitter = event.submitter || form.querySelector('button[type="submit"], input[type="submit"]');
    if (!submitter || submitter.disabled) return;
    if (form.dataset.submitting === "true") {
      event.preventDefault();
      return;
    }
    form.dataset.submitting = "true";
    submitter.disabled = true;
    submitter.setAttribute("aria-busy", "true");
    submitter.dataset.originalLabel = submitter.textContent.trim();
    const label = submitter.dataset.pendingLabel || "Saving…";
    if (submitter.tagName === "BUTTON") {
      const spinner = document.createElement("span");
      spinner.dataset.spinner = "";
      spinner.setAttribute("aria-hidden", "true");
      submitter.replaceChildren(spinner, document.createTextNode(` ${label}`));
    }
  });

  if (reducedMotion) document.documentElement.classList.add("reduced-motion");
})();
