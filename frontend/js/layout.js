const NAV = [['dashboard', 'نظرة عامة'], ['knowledge', 'قاعدة المعرفة'], ['bot', 'بوت تليجرام'], ['conversations', 'المحادثات', 2], ['company', 'ملف الشركة'], ['billing', 'الاشتراك']];

const DEFAULT_THEME = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
const DEFAULT_LANG = (document.documentElement.lang || 'ar').toLowerCase().startsWith('en') ? 'en' : 'ar';

function applyTheme(theme) {
  const resolved = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', resolved);
  document.body.setAttribute('data-theme', resolved);
  document.documentElement.style.colorScheme = resolved;
  localStorage.setItem('td_theme', resolved);

  document.querySelectorAll('.theme-toggle').forEach((btn) => {
    btn.textContent = resolved === 'dark' ? '☀' : '☾';
    btn.title = resolved === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
    btn.setAttribute('aria-label', resolved === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
  });
}

function applyLanguage(lang) {
  const resolved = lang === 'en' ? 'en' : 'ar';
  document.documentElement.lang = resolved;
  document.documentElement.dir = resolved === 'en' ? 'ltr' : 'rtl';
  document.body.dir = resolved === 'en' ? 'ltr' : 'rtl';
  document.body.setAttribute('data-lang', resolved);
  localStorage.setItem('td_lang', resolved);

  document.querySelectorAll('.lang-toggle').forEach((btn) => {
    btn.textContent = resolved === 'en' ? 'AR' : 'EN';
    btn.title = resolved === 'en' ? 'Switch to Arabic' : 'Switch to English';
    btn.setAttribute('aria-label', resolved === 'en' ? 'Switch to Arabic' : 'Switch to English');
  });

  const searchInput = document.querySelector('.top input');
  if (searchInput) {
    searchInput.placeholder = resolved === 'en' ? 'Search conversations and files' : 'ابحث في المحادثات والملفات';
    searchInput.setAttribute('aria-label', resolved === 'en' ? 'Search' : 'بحث');
  }

  const statusBadge = document.querySelector('.top-status');
  if (statusBadge) {
    statusBadge.textContent = resolved === 'en' ? 'Bot online' : '● البوت شغال';
  }
}

function bindGlobalToggles() {
  document.querySelectorAll('.theme-toggle').forEach((button) => {
    button.onclick = () => {
      const nextTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(nextTheme);
    };
  });

  document.querySelectorAll('.lang-toggle').forEach((button) => {
    button.onclick = () => {
      const nextLang = document.documentElement.lang === 'en' ? 'ar' : 'en';
      applyLanguage(nextLang);
    };
  });
}

(() => {
  const storedTheme = localStorage.getItem('td_theme') || DEFAULT_THEME;
  const storedLang = localStorage.getItem('td_lang') || DEFAULT_LANG;
  const pageName = (document.body.dataset.page || '').toLowerCase();

  applyTheme(storedTheme);
  applyLanguage(storedLang);
  bindGlobalToggles();

  const isMarketingPage = pageName === 'home' || pageName === 'login' || document.body.classList.contains('landing-page') || document.body.classList.contains('login-page');
  const hasAppShell = document.querySelector('.top');
  if (isMarketingPage || hasAppShell || !document.querySelector('main')) return;

  const cur = pageName || 'dashboard';
  const top = `
    <header class="top">
      <a class="logo" href="dashboard.html"><span class="brand-mark">T</span><span>TeleDesk</span></a>
      <nav class="row">
        <a href="dashboard.html">${storedLang === 'en' ? 'Overview' : 'نظرة عامة'}</a>
        <a href="knowledge.html">${storedLang === 'en' ? 'Knowledge base' : 'قاعدة المعرفة'}</a>
        <a href="bot.html">${storedLang === 'en' ? 'Telegram bot' : 'بوت تليجرام'}</a>
        <a href="conversations.html">${storedLang === 'en' ? 'Conversations' : 'المحادثات'}</a>
        <a href="company.html">${storedLang === 'en' ? 'Company profile' : 'ملف الشركة'}</a>
        <a href="billing.html">${storedLang === 'en' ? 'Subscription' : 'الاشتراك'}</a>
      </nav>
      <div class="top-actions">
        <button class="theme-toggle" type="button" aria-label="Toggle theme">${storedTheme === 'dark' ? '☀' : '☾'}</button>
      </div>
      <input placeholder="${storedLang === 'en' ? 'Search conversations and files' : 'ابحث في المحادثات والملفات'}" aria-label="${storedLang === 'en' ? 'Search' : 'بحث'}">
      <span class="tag top-status">${storedLang === 'en' ? 'Bot online' : '● البوت شغال'}</span>
    </header>`;

  const side = `<nav class="side">${NAV.map(([k, t, n]) => `<a href="${k}.html" class="${k === cur ? 'on' : ''}">${storedLang === 'en' ? (k === 'dashboard' ? 'Overview' : k === 'knowledge' ? 'Knowledge base' : k === 'bot' ? 'Telegram bot' : k === 'conversations' ? 'Conversations' : k === 'company' ? 'Company profile' : 'Subscription') : t}${n ? `<span class="tag a">${n}</span>` : ''}</a>`).join('')}
    <div class="plan"><div class="row sp"><b>${storedLang === 'en' ? 'Pro plan' : 'خطة Pro'}</b><span>14%</span></div><div class="bar"><i style="width:14%"></i></div><div class="mut">${storedLang === 'en' ? '1,429 of 10,000 messages' : '1,429 من 10,000 رسالة'}</div></div></nav>`;

  document.body.insertAdjacentHTML('afterbegin', top + '<div class="wrap">' + side + '</div>');
  document.querySelector('.wrap').appendChild(document.querySelector('main'));
  bindGlobalToggles();
})();
