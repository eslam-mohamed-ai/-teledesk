// Centralized API helpers for the TeleDesk frontend.
const OFFLINE_MESSAGE = 'The backend is currently unavailable. Start the FastAPI service and try again.';
const BASE = (window.TeleDeskApiBase || '').replace(/\/$/, '');

const token = () => localStorage.getItem('td_token');

function showBackendNotice(message = OFFLINE_MESSAGE) {
  const notice = document.getElementById('backendNotice');
  if (notice) {
    notice.textContent = message;
    notice.style.display = 'block';
  }
}

async function api(path, opts = {}) {
  const isForm = opts.body instanceof FormData;

  try {
    const response = await fetch(BASE + '/api' + path, {
      ...opts,
      headers: {
        ...(isForm ? {} : { 'Content-Type': 'application/json' }),
        ...(token() ? { Authorization: 'Bearer ' + token() } : {}),
        ...opts.headers
      },
      body: opts.body && !isForm && typeof opts.body !== 'string'
        ? JSON.stringify(opts.body)
        : opts.body
    });

    if (response.status === 401) {
      localStorage.removeItem('td_token');
      location.href = 'login.html';
      throw new Error('Your session has expired. Please sign in again.');
    }

    const text = await response.text();
    const data = text ? JSON.parse(text) : {};

    if (!response.ok) {
      const message = data.detail || data.message || 'Something went wrong. Please try again.';
      if (response.status === 404 || response.status >= 500) {
        showBackendNotice();
        const offline = new Error(OFFLINE_MESSAGE);
        offline.offline = true;
        throw offline;
      }
      throw new Error(message);
    }

    return data;
  } catch (error) {
    const message = error && error.message ? error.message : 'Unexpected error';
    const isOffline = error instanceof TypeError || /failed to fetch|network/i.test(message);

    if (isOffline) {
      showBackendNotice();
      const wrapped = new Error(OFFLINE_MESSAGE);
      wrapped.offline = true;
      throw wrapped;
    }

    throw error;
  }
}

const API = {
  signup: (d) => api('/auth/register', { method: 'POST', body: d }),
  login: (d) => api('/auth/login', { method: 'POST', body: d }),
  demo: () => api('/auth/demo', { method: 'POST' }),
  me: () => api('/auth/me'),

  statsOverview: (days = 7) => api('/stats/overview?days=' + encodeURIComponent(days)),
  billing: () => api('/billing'),
  conversations: (status = 'all', q = '') => api('/conversations?status=' + encodeURIComponent(status) + '&q=' + encodeURIComponent(q)),
  conversationDetail: (id) => api('/conversations/' + id),
  conversationTake: (id) => api('/conversations/' + id + '/take', { method: 'POST' }),
  conversationClose: (id) => api('/conversations/' + id + '/close', { method: 'POST' }),
  conversationNote: (id, note) => api('/conversations/' + id + '/note', { method: 'POST', body: { note } }),
  conversationReply: (id, text) => api('/conversations/' + id + '/reply', { method: 'POST', body: { text } }),

  documents: () => api('/documents'),
  upload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api('/documents/upload', { method: 'POST', body: form });
  },
  addText: (d) => api('/documents/text', { method: 'POST', body: d }),
  deleteDoc: (id) => api('/documents/' + id, { method: 'DELETE' }),

  connectBot: (tokenValue) => api('/bots/connect', { method: 'POST', body: { token: tokenValue } }),
  testBot: (d) => api('/bots/test', { method: 'POST', body: d }),
  bot: () => api('/bots'),
  toggleBot: () => api('/bots/toggle', { method: 'POST' }),
  disconnectBot: () => api('/bots/disconnect', { method: 'POST' }),

  company: () => api('/company'),
  saveCompany: (d) => api('/company', { method: 'PUT', body: d })
};

async function authForm(event, kind) {
  event.preventDefault();
  const form = event.currentTarget;
  const values = Object.fromEntries(new FormData(form));
  const errorElement = document.getElementById('err');

  if (errorElement) errorElement.textContent = '';

  try {
    const response = await API[kind](values);

    if (!response || !response.token) {
      throw new Error('The server did not return a session token.');
    }

    localStorage.setItem('td_token', response.token);
    location.href = 'dashboard.html';
  } catch (error) {
    const message = error && error.message ? error.message : 'Authentication failed';
    if (errorElement) {
      errorElement.textContent = message;
    } else {
      alert(message);
    }
  }
}

window.TeleDeskApi = API;
