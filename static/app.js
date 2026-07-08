const state = {
  user: null,
  goals: [],
  invites: [],
};

const authView = document.querySelector("#authView");
const appView = document.querySelector("#appView");
const accountForm = document.querySelector("#accountForm");
const goalForm = document.querySelector("#goalForm");
const goalGrid = document.querySelector("#goalGrid");
const goalCount = document.querySelector("#goalCount");
const inviteList = document.querySelector("#inviteList");
const trackerEnabled = document.querySelector("#trackerEnabled");
const trackerFields = document.querySelector("#trackerFields");
const welcomeTitle = document.querySelector("#welcomeTitle");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Something went wrong");
  }
  return payload;
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function selectedRewards(form) {
  return [...form.querySelectorAll("input[name='reward_preferences']:checked")].map((input) => input.value);
}

function showApp() {
  authView.classList.add("hidden");
  appView.classList.remove("hidden");
  welcomeTitle.textContent = `${state.user.name}'s goals`;
}

function showAuth() {
  appView.classList.add("hidden");
  authView.classList.remove("hidden");
}

function splitTime(seconds) {
  const total = Math.max(0, seconds);
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  return { days, hours, minutes, secs };
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function priorityLabel(priority) {
  return ["Low", "Gentle", "Steady", "Important", "High stakes"][priority - 1] || "Steady";
}

function renderCountdown(goal) {
  if (goal.status === "complete") {
    return `<div class="countdown"><div class="time-box"><strong>Done</strong><span>complete</span></div></div>`;
  }
  const time = splitTime(goal.seconds_remaining);
  return `
    <div class="countdown" data-goal-countdown="${goal.id}">
      <div class="time-box"><strong>${time.days}</strong><span>days</span></div>
      <div class="time-box"><strong>${time.hours}</strong><span>hours</span></div>
      <div class="time-box"><strong>${time.minutes}</strong><span>mins</span></div>
      <div class="time-box"><strong>${time.secs}</strong><span>secs</span></div>
    </div>
  `;
}

function renderTracker(goal) {
  if (!goal.trackers.length) return "";
  const tracker = goal.trackers[0];
  const percent = Math.min(100, Math.round((tracker.current / tracker.target) * 100));
  return `
    <div class="tracker-box">
      <p><strong>${escapeHtml(tracker.metric)}</strong>: ${tracker.current} / ${tracker.target} ${escapeHtml(tracker.unit)}</p>
      <div class="progress-track"><div class="progress-fill" style="width:${percent}%"></div></div>
      <div class="row">
        <input type="number" min="0" step="1" value="${tracker.current}" data-tracker-input="${tracker.id}" aria-label="Tracker value" />
        <button class="small" data-update-tracker="${tracker.id}">Update</button>
      </div>
    </div>
  `;
}

function renderGoal(goal) {
  const isOwner = goal.user_id === state.user.id;
  const completeButton = isOwner && goal.status !== "complete"
    ? `<button class="small" data-complete="${goal.id}">Mark complete</button>`
    : "";
  return `
    <article class="goal-card ${goal.status === "complete" ? "complete" : ""}">
      <div class="card-top">
        <div>
          <h3>${escapeHtml(goal.title)}</h3>
          <p>${escapeHtml(goal.category)} · ${escapeHtml(goal.recurrence)} · ${priorityLabel(goal.priority)}</p>
        </div>
        <span class="badge">${goal.status === "complete" ? "Complete" : "Active"}</span>
      </div>
      ${renderCountdown(goal)}
      ${goal.notes ? `<p>${escapeHtml(goal.notes)}</p>` : ""}
      <div class="quote">
        <p><strong>Coaching nudge</strong></p>
        <p>${escapeHtml(goal.motivation.text)}</p>
        <p>${escapeHtml(goal.motivation.label)}</p>
      </div>
      ${renderTracker(goal)}
      <div class="reward">
        <p><strong>Reward preview</strong></p>
        <p>${escapeHtml(goal.reward.idea)}</p>
      </div>
      <div class="share-box">
        <div class="row">
          <input type="email" placeholder="friend@example.com" data-share-input="${goal.id}" />
          <button class="small" data-share="${goal.id}">Share</button>
        </div>
      </div>
      <div class="cheer-box">
        <div class="row">
          <input placeholder="Send a cheer or accountability note" data-cheer-input="${goal.id}" />
          <button class="small" data-cheer="${goal.id}">Send</button>
        </div>
        ${goal.cheers.map((cheer) => `<p><strong>${escapeHtml(cheer.from_name)}:</strong> ${escapeHtml(cheer.message)}</p>`).join("")}
      </div>
      <div class="mini-actions">${completeButton}</div>
    </article>
  `;
}

function renderInvites() {
  if (!state.invites.length) {
    inviteList.innerHTML = `<p>No pending invites yet.</p>`;
    return;
  }
  inviteList.innerHTML = state.invites.map((invite) => `
    <div class="invite-card">
      <strong>${escapeHtml(invite.title)}</strong>
      <p>Shared by ${escapeHtml(invite.owner_name)} · ${escapeHtml(invite.category)}</p>
      <button class="small" data-accept-invite="${invite.id}">Accept</button>
    </div>
  `).join("");
}

function renderGoals() {
  goalCount.textContent = `${state.goals.filter((goal) => goal.status !== "complete").length} active`;
  goalGrid.innerHTML = state.goals.length
    ? state.goals.map(renderGoal).join("")
    : `<p>No tiles yet. Create one goal and give future-you a starting line.</p>`;
}

function updateCountdownDisplays() {
  state.goals.forEach((goal) => {
    if (goal.status === "complete") return;
    const node = document.querySelector(`[data-goal-countdown='${goal.id}']`);
    if (!node) return;
    const time = splitTime(goal.seconds_remaining);
    const values = [time.days, time.hours, time.minutes, time.secs];
    node.querySelectorAll("strong").forEach((item, index) => {
      item.textContent = values[index];
    });
  });
}

async function refresh() {
  const [goals, invites] = await Promise.all([
    api("/api/goals"),
    api("/api/invites"),
  ]);
  state.goals = goals.goals;
  state.invites = invites.invites;
  renderGoals();
  renderInvites();
}

accountForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = formValues(accountForm);
  values.reward_preferences = selectedRewards(accountForm);
  try {
    const payload = await api("/api/account", { method: "POST", body: JSON.stringify(values) });
    state.user = payload.user;
    showApp();
    await refresh();
  } catch (error) {
    alert(error.message);
  }
});

goalForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = formValues(goalForm);
  values.tracker = {
    enabled: trackerEnabled.checked,
    metric: values.tracker_metric,
    target: values.tracker_target,
    unit: values.tracker_unit,
  };
  try {
    await api("/api/goals", { method: "POST", body: JSON.stringify(values) });
    goalForm.reset();
    trackerFields.classList.add("hidden");
    await refresh();
  } catch (error) {
    alert(error.message);
  }
});

trackerEnabled.addEventListener("change", () => {
  trackerFields.classList.toggle("hidden", !trackerEnabled.checked);
});

document.querySelector("#logoutBtn").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST", body: "{}" });
  state.user = null;
  showAuth();
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;

  try {
    if (button.dataset.complete) {
      await api("/api/goals/complete", { method: "POST", body: JSON.stringify({ goal_id: button.dataset.complete }) });
      await refresh();
    }
    if (button.dataset.updateTracker) {
      const input = document.querySelector(`[data-tracker-input='${button.dataset.updateTracker}']`);
      await api("/api/trackers/update", {
        method: "POST",
        body: JSON.stringify({ tracker_id: button.dataset.updateTracker, current: input.value }),
      });
      await refresh();
    }
    if (button.dataset.share) {
      const input = document.querySelector(`[data-share-input='${button.dataset.share}']`);
      await api("/api/share", { method: "POST", body: JSON.stringify({ goal_id: button.dataset.share, email: input.value }) });
      input.value = "";
      await refresh();
    }
    if (button.dataset.cheer) {
      const input = document.querySelector(`[data-cheer-input='${button.dataset.cheer}']`);
      await api("/api/cheer", { method: "POST", body: JSON.stringify({ goal_id: button.dataset.cheer, message: input.value }) });
      input.value = "";
      await refresh();
    }
    if (button.dataset.acceptInvite) {
      await api("/api/invites/accept", { method: "POST", body: JSON.stringify({ share_id: button.dataset.acceptInvite }) });
      await refresh();
    }
  } catch (error) {
    alert(error.message);
  }
});

async function boot() {
  try {
    const payload = await api("/api/me");
    state.user = payload.user;
    if (state.user) {
      showApp();
      await refresh();
    } else {
      showAuth();
    }
  } catch {
    showAuth();
  }
}

setInterval(() => {
  state.goals = state.goals.map((goal) => ({
    ...goal,
    seconds_remaining: goal.status === "complete" ? goal.seconds_remaining : goal.seconds_remaining - 1,
  }));
  if (state.user) updateCountdownDisplays();
}, 1000);

boot();
