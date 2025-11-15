document.addEventListener("DOMContentLoaded", () => {
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    const dismissSeconds = alert.dataset.dismissAfter;
    if (dismissSeconds) {
      setTimeout(() => {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        bsAlert.close();
      }, parseInt(dismissSeconds, 10) * 1000);
    }
  });

  const threadEl = document.getElementById("message-thread");
  if (threadEl) {
    const pollUrl = threadEl.dataset.pollUrl;
    let lastTimestamp = threadEl.dataset.lastTimestamp;
    const existingIds = new Set(
      Array.from(threadEl.querySelectorAll("[data-message-id]")).map((node) => node.dataset.messageId),
    );

    const renderMessage = (message) => {
      if (existingIds.has(String(message.message_id))) {
        return;
      }
      existingIds.add(String(message.message_id));
      lastTimestamp = message.timestamp;

      const wrapper = document.createElement("div");
      const isSelf = Number(message.sender_id) === Number(threadEl.dataset.currentUserId || 0);
      wrapper.className = `mb-3 ${isSelf ? "text-end" : ""}`;
      wrapper.dataset.messageId = message.message_id;
      wrapper.dataset.timestamp = message.timestamp;

      const header = document.createElement("div");
      header.className = `d-flex justify-content-between ${isSelf ? "flex-row-reverse" : ""}`;

      const nameSpan = document.createElement("span");
      nameSpan.className = "fw-semibold";
      nameSpan.textContent = isSelf ? "You" : "Contact";

      const timeSpan = document.createElement("span");
      timeSpan.className = "text-muted small";
      timeSpan.textContent = new Date(message.timestamp).toLocaleString();

      header.appendChild(nameSpan);
      header.appendChild(timeSpan);

      const body = document.createElement("div");
      body.className = `mt-2 p-3 rounded ${isSelf ? "bg-primary text-white" : "bg-body-secondary"}`;
      body.textContent = message.content;

      wrapper.appendChild(header);
      wrapper.appendChild(body);
      threadEl.appendChild(wrapper);
      threadEl.scrollTop = threadEl.scrollHeight;
    };

    if (pollUrl) {
      setInterval(() => {
        if (!lastTimestamp) {
          const latest = threadEl.querySelector("[data-timestamp]:last-child");
          if (latest) {
            lastTimestamp = latest.dataset.timestamp;
          } else {
            return;
          }
        }
        const url = new URL(pollUrl, window.location.origin);
        url.searchParams.set("ts", lastTimestamp);
        fetch(url.toString(), { headers: { Accept: "application/json" } })
          .then((response) => {
            if (!response.ok) {
              throw new Error("Network response was not ok");
            }
            return response.json();
          })
          .then((messages) => {
            messages.forEach(renderMessage);
          })
          .catch(() => {
            // Silently ignore polling errors
          });
      }, 6000);
    }
  }
});

