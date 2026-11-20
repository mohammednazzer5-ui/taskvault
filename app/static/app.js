"use strict";

const STATUS_LABELS = { todo: "To do", in_progress: "In progress", done: "Done" };

let token = localStorage.getItem("token");
let currentUser = null;
let editingId = null;

const $ = (id) => document.getElementById(id);

/* ---------- helpers ---------- */

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = "Bearer " + token;

  const res = await fetch("/api" + path, { ...options, headers });
  let data = null;
  try {
    data = await res.json();
  } catch (_) {
    /* empty body (e.g. 204) */
  }

  if (res.status === 401 && token) {
    logout();
  }
  if (!res.ok) {
    throw new Error((data && data.error) || "Something went wrong");
  }
  return data;
}

function showError(id, message) {
  const el = $(id);
  el.textContent = message || "";
  el.hidden = !message;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text; // textContent = no HTML injection
  return node;
}

/* ---------- auth ---------- */

function setSession(data) {
  token = data.token;
  currentUser = data.user;
  localStorage.setItem("token", token);
  showApp();
}

function logout() {
  token = null;
  currentUser = null;
  localStorage.removeItem("token");
  showAuth();
}

function selectTab(which) {
  const login = which === "login";
  $("tab-login").classList.toggle("active", login);
  $("tab-register").classList.toggle("active", !login);
  $("login-panel").hidden = !login;
  $("register-panel").hidden = login;
  showError("auth-error", "");
}

async function doLogin() {
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("login-email").value,
        password: $("login-password").value,
      }),
    });
    $("login-password").value = "";
    setSession(data);
  } catch (err) {
    showError("auth-error", err.message);
  }
}

async function doRegister() {
  try {
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        name: $("reg-name").value,
        email: $("reg-email").value,
        password: $("reg-password").value,
      }),
    });
    $("reg-password").value = "";
    setSession(data);
  } catch (err) {
    showError("auth-error", err.message);
  }
}

/* ---------- views ---------- */

function showAuth() {
  $("auth-view").hidden = false;
  $("app-view").hidden = true;
  $("user-box").hidden = true;
}

function showApp() {
  $("auth-view").hidden = true;
  $("app-view").hidden = false;
  $("user-box").hidden = false;
  $("user-label").textContent =
    currentUser.name + (currentUser.role === "admin" ? " (admin)" : "");
  resetForm();
  loadTasks();
  if (currentUser.role === "admin") {
    $("admin-card").hidden = false;
    loadUsers();
  } else {
    $("admin-card").hidden = true;
  }
}

/* ---------- tasks ---------- */

function resetForm() {
  editingId = null;
  $("task-title").value = "";
  $("task-desc").value = "";
  $("task-status").value = "todo";
  $("form-title").textContent = "New task";
  $("task-save").textContent = "Add task";
  $("task-cancel").hidden = true;
  showError("task-error", "");
}

function startEdit(task) {
  editingId = task.id;
  $("task-title").value = task.title;
  $("task-desc").value = task.description;
  $("task-status").value = task.status;
  $("form-title").textContent = "Edit task";
  $("task-save").textContent = "Save changes";
  $("task-cancel").hidden = false;
  $("task-title").focus();
}

async function saveTask() {
  const body = JSON.stringify({
    title: $("task-title").value,
    description: $("task-desc").value,
    status: $("task-status").value,
  });
  try {
    if (editingId) {
      await api("/tasks/" + editingId, { method: "PATCH", body });
    } else {
      await api("/tasks", { method: "POST", body });
    }
    resetForm();
    loadTasks();
  } catch (err) {
    showError("task-error", err.message);
  }
}

async function loadTasks() {
  try {
    const filter = $("filter").value;
    const query = filter ? "?status=" + encodeURIComponent(filter) : "";
    const data = await api("/tasks" + query);
    renderTasks(data.tasks);
  } catch (err) {
    showError("task-error", err.message);
  }
}

function renderTasks(tasks) {
  const list = $("task-list");
  list.replaceChildren();
  $("empty").hidden = tasks.length > 0;

  for (const task of tasks) {
    const item = el("li", "task" + (task.status === "done" ? " done" : ""));

    const info = el("div");
    info.append(el("div", "task-title", task.title));
    if (task.description) info.append(el("p", "task-desc", task.description));

    const actions = el("div", "task-actions");

    const status = el("select");
    status.setAttribute("aria-label", "Change status");
    for (const [value, label] of Object.entries(STATUS_LABELS)) {
      const option = el("option", "", label);
      option.value = value;
      option.selected = value === task.status;
      status.append(option);
    }
    status.addEventListener("change", async () => {
      try {
        await api("/tasks/" + task.id, {
          method: "PATCH",
          body: JSON.stringify({ status: status.value }),
        });
        loadTasks();
      } catch (err) {
        showError("task-error", err.message);
      }
    });

    const edit = el("button", "btn btn-ghost btn-small", "Edit");
    edit.type = "button";
    edit.addEventListener("click", () => startEdit(task));

    const del = el("button", "btn btn-ghost btn-small btn-danger", "Delete");
    del.type = "button";
    del.addEventListener("click", async () => {
      if (!confirm("Delete this task?")) return;
      try {
        await api("/tasks/" + task.id, { method: "DELETE" });
        if (editingId === task.id) resetForm();
        loadTasks();
      } catch (err) {
        showError("task-error", err.message);
      }
    });

    actions.append(status, edit, del);
    item.append(info, actions);
    list.append(item);
  }
}

/* ---------- admin ---------- */

async function loadUsers() {
  try {
    const data = await api("/admin/users");
    const body = $("user-rows");
    body.replaceChildren();
    showError("admin-error", "");

    for (const user of data.users) {
      const row = el("tr");
      row.append(
        el("td", "", user.name),
        el("td", "", user.email),
        el("td", "", user.role),
        el("td", "", String(user.task_count))
      );

      const cell = el("td");
      if (user.id !== currentUser.id) {
        const toggle = el(
          "button",
          "btn btn-ghost btn-small",
          user.role === "admin" ? "Make user" : "Make admin"
        );
        toggle.type = "button";
        toggle.addEventListener("click", async () => {
          try {
            await api("/admin/users/" + user.id, {
              method: "PATCH",
              body: JSON.stringify({ role: user.role === "admin" ? "user" : "admin" }),
            });
            loadUsers();
          } catch (err) {
            showError("admin-error", err.message);
          }
        });

        const del = el("button", "btn btn-ghost btn-small btn-danger", "Delete");
        del.type = "button";
        del.addEventListener("click", async () => {
          if (!confirm("Delete " + user.email + " and all their tasks?")) return;
          try {
            await api("/admin/users/" + user.id, { method: "DELETE" });
            loadUsers();
          } catch (err) {
            showError("admin-error", err.message);
          }
        });
        cell.append(toggle, " ", del);
      } else {
        cell.append(el("span", "muted", "You"));
      }
      row.append(cell);
      body.append(row);
    }
  } catch (err) {
    showError("admin-error", err.message);
  }
}

/* ---------- wiring ---------- */

$("tab-login").addEventListener("click", () => selectTab("login"));
$("tab-register").addEventListener("click", () => selectTab("register"));
$("login-btn").addEventListener("click", doLogin);
$("register-btn").addEventListener("click", doRegister);
$("logout-btn").addEventListener("click", logout);
$("task-save").addEventListener("click", saveTask);
$("task-cancel").addEventListener("click", resetForm);
$("filter").addEventListener("change", loadTasks);

for (const id of ["login-email", "login-password"]) {
  $(id).addEventListener("keydown", (e) => e.key === "Enter" && doLogin());
}
for (const id of ["reg-name", "reg-email", "reg-password"]) {
  $(id).addEventListener("keydown", (e) => e.key === "Enter" && doRegister());
}

(async function init() {
  if (!token) return showAuth();
  try {
    const data = await api("/auth/me");
    currentUser = data.user;
    showApp();
  } catch (_) {
    showAuth();
  }
})();
