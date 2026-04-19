async function submitForm(formId, url, statusId) {
  document.getElementById(formId).addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = document.getElementById(statusId);
    status.textContent = "Printing...";
    const res = await fetch(url, { method: "POST", body: new FormData(e.target) });
    if (res.ok) {
      status.textContent = "Done!";
    } else {
      const data = await res.json().catch(() => ({}));
      status.textContent = "Error: " + (data.detail ?? res.status);
    }
  });
}
submitForm("text-form", "/print/text", "text-status");
submitForm("image-form", "/print/image", "image-status");
