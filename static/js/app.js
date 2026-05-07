/* ─── Black Pearl — Frontend Logic ───────────────────────────── */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ── i18n ─────────────────────────────────────────────────────────
const translations = {
    pt: {
        skipLink: 'Pular para o conteudo principal',
        logoTitle: 'Black Pearl',
        autoTag: 'Auto-tag',
        changeLang: 'Mudar idioma',
        settingsCookiesTitle: 'Configuracoes de Cookies',
        settings: 'Configuracoes',
        closeSettings: 'Fechar configuracoes',
        cookiesYT: 'Cookies do YouTube',
        cookiesDesc: 'Para evitar o erro "Sign in to confirm you\'re not a bot", faca upload de um arquivo cookies.txt com os cookies da sua sessao do YouTube.',
        cookiesChecking: 'Verificando...',
        uploadCookies: 'Upload cookies.txt',
        removeCookies: 'Remover cookies',
        cookieHelpTitle: 'Como exportar cookies do Librewolf/Firefox?',
        cookieHelpStep5: 'Faca upload desse arquivo aqui',
        searchPlaceholder: 'Cole um link do YouTube ou pesquise por nome...',
        search: 'Buscar',
        searchingResults: 'Buscando resultados...',
        readyToDownload: 'Pronto para baixar',
        emptyStateDesc: 'Cole um link do YouTube ou pesquise pelo nome de uma musica, artista ou video.',
        results: 'Resultados',
        footerText: '\u00a9 2024 Black Pearl. Ferramenta de download de audio do YouTube.',
        privacy: 'Privacidade',
        terms: 'Termos',
        downloadAudio: 'Baixar audio',
        download: 'Baixar',
        searching: 'Buscando...',
        resultsCount: (n) => `${n} resultado${n !== 1 ? 's' : ''}`,
        preparing: 'Preparando...',
        downloading: 'Baixando...',
        fileSaved: (name) => `${name || 'Arquivo'} salvo!`,
        done: 'Pronto \u2713',
        error: 'Erro',
        retry: 'Tentar novamente',
        cookiesLoaded: 'Cookies carregados (cookies.txt)',
        noCookies: 'Nenhum cookies configurado',
        cookiesError: 'Erro ao verificar cookies',
        cookiesUpdated: 'Cookies atualizados!',
        cookiesUploadError: 'Erro ao enviar cookies',
        cookiesRemoved: 'Cookies removidos',
        cookiesRemoveError: 'Erro ao remover cookies',
        unknownError: 'Erro desconhecido',
    },
    en: {
        skipLink: 'Skip to main content',
        logoTitle: 'Black Pearl',
        autoTag: 'Auto-tag',
        changeLang: 'Change language',
        settingsCookiesTitle: 'Cookie Settings',
        settings: 'Settings',
        closeSettings: 'Close settings',
        cookiesYT: 'YouTube Cookies',
        cookiesDesc: 'To avoid the "Sign in to confirm you\'re not a bot" error, upload a cookies.txt file with your YouTube session cookies.',
        cookiesChecking: 'Checking...',
        uploadCookies: 'Upload cookies.txt',
        removeCookies: 'Remove cookies',
        cookieHelpTitle: 'How to export cookies from Librewolf/Firefox?',
        cookieHelpStep5: 'Upload that file here',
        searchPlaceholder: 'Paste a YouTube link or search by name...',
        search: 'Search',
        searchingResults: 'Searching results...',
        readyToDownload: 'Ready to download',
        emptyStateDesc: 'Paste a YouTube link or search by song name, artist, or video.',
        results: 'Results',
        footerText: '\u00a9 2024 Black Pearl. YouTube audio download tool.',
        privacy: 'Privacy',
        terms: 'Terms',
        downloadAudio: 'Download audio',
        download: 'Download',
        searching: 'Searching...',
        resultsCount: (n) => `${n} result${n !== 1 ? 's' : ''}`,
        preparing: 'Preparing...',
        downloading: 'Downloading...',
        fileSaved: (name) => `${name || 'File'} saved!`,
        done: 'Done \u2713',
        error: 'Error',
        retry: 'Try again',
        unknownError: 'Unknown error',
        cookiesLoaded: 'Cookies loaded (cookies.txt)',
        noCookies: 'No cookies configured',
        cookiesError: 'Error checking cookies',
        cookiesUpdated: 'Cookies updated!',
        cookiesUploadError: 'Error uploading cookies',
        cookiesRemoved: 'Cookies removed',
        cookiesRemoveError: 'Error removing cookies',
    },
};

const htmlTranslations = {
    pt: {
        cookieHelpStep1: 'Instale a extensao <a href="https://addons.mozilla.org/en-US/firefox-addon/get-cookiestxt-locally/" target="_blank">"Get cookies.txt LOCALLY"</a> no Librewolf',
        cookieHelpStep2: 'Faca login no <a href="https://www.youtube.com" target="_blank">YouTube</a>',
        cookieHelpStep3: 'Na pagina do YouTube, clique na extensao <strong>"Get cookies.txt LOCALLY"</strong> na barra de ferramentas',
        cookieHelpStep4: 'Clique em <strong>"Export"</strong> \u2014 vai baixar um arquivo <code>cookies.txt</code>',
        cookieHelpImportant: '<strong>Importante:</strong> O arquivo deve estar no formato Netscape (com tabs entre as colunas).<br>Nao copie e cole cookies manualmente \u2014 use a extensao pra exportar!',
        searchHint: 'Aceita link do YouTube <span>youtube.com/watch?v=...</span> ou texto livre <span>nome da musica</span>',
    },
    en: {
        cookieHelpStep1: 'Install the <a href="https://addons.mozilla.org/en-US/firefox-addon/get-cookiestxt-locally/" target="_blank">"Get cookies.txt LOCALLY"</a> extension on Librewolf',
        cookieHelpStep2: 'Log in to <a href="https://www.youtube.com" target="_blank">YouTube</a>',
        cookieHelpStep3: 'On the YouTube page, click the <strong>"Get cookies.txt LOCALLY"</strong> extension in the toolbar',
        cookieHelpStep4: 'Click <strong>"Export"</strong> \u2014 it will download a <code>cookies.txt</code> file',
        cookieHelpImportant: '<strong>Important:</strong> The file must be in Netscape format (with tabs between columns).<br>Don\'t copy and paste cookies manually \u2014 use the extension to export!',
        searchHint: 'Accepts YouTube link <span>youtube.com/watch?v=...</span> or free text <span>song name</span>',
    },
};

let currentLocale = localStorage.getItem('bp-locale') || 'pt';
const t = (key, ...args) => {
    const val = translations[currentLocale]?.[key] ?? translations.pt[key];
    return typeof val === 'function' ? val(...args) : val;
};

function applyTranslations() {
    document.documentElement.lang = currentLocale === 'pt' ? 'pt-BR' : 'en';
    $$('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        if (translations[currentLocale]?.[key] !== undefined) el.textContent = t(key);
    });
    $$('[data-i18n-html]').forEach(el => {
        const key = el.dataset.i18nHtml;
        const val = htmlTranslations[currentLocale]?.[key] ?? htmlTranslations.pt[key];
        if (val !== undefined) el.replaceChildren(document.createRange().createContextualFragment(val));
    });
    $$('[data-i18n-placeholder]').forEach(el => {
        el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    $$('[data-i18n-aria]').forEach(el => {
        el.setAttribute('aria-label', t(el.dataset.i18nAria));
    });
    $$('[data-i18n-title]').forEach(el => {
        el.title = t(el.dataset.i18nTitle);
    });
}

// ── State ────────────────────────────────────────────────────────
const state = {
    results: [],
    activeDownloads: new Map(), // task_id -> interval
};
let lastFocusedElement = null;

// ── Elements ─────────────────────────────────────────────────────
const searchInput = $('#search-input');
const searchBtn = $('#search-btn');
const resultsSection = $('#results-section');
const resultsList = $('#results-list');
const resultsHeader = $('#results-header');
const loadingEl = $('#loading');
const emptyState = $('#empty-state');

// ── Utilities ────────────────────────────────────────────────────
function formatDuration(seconds) {
    if (!seconds) return '';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
}

function formatViews(count) {
    if (!count) return '';
    if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M views`;
    if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K views`;
    return `${count} views`;
}

function formatSpeed(speed) {
    if (!speed) return '';
    if (speed >= 1_048_576) return `${(speed / 1_048_576).toFixed(1)} MB/s`;
    return `${(speed / 1024).toFixed(0)} KB/s`;
}

function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${type === 'success' ? '&#10003;' : '&#10007;'}</span>
        <span>${message}</span>
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

// ── API ──────────────────────────────────────────────────────────
async function apiSearch(query) {
    const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Erro na busca');
    }
    return res.json();
}

async function apiDownload(url, title) {
    const enrich = document.getElementById('enrich-toggle')?.checked ?? true;
    const res = await fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, title, enrich }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Erro no download');
    }
    return res.json();
}

async function apiProgress(taskId) {
    const res = await fetch(`/api/progress/${taskId}`);
    if (!res.ok) return null;
    return res.json();
}

// ── Rendering ────────────────────────────────────────────────────
function renderVideoCard(video) {
    const card = document.createElement('div');
    card.className = 'video-card';
    card.dataset.url = video.url;
    card.innerHTML = `
        <div class="video-thumb">
            <img src="${video.thumbnail}" alt="${video.title}" loading="lazy"
                 onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 160 90%22><rect fill=%22oklch(0.25%200.008%20285)%22 width=%22160%22 height=%2290%22/><text x=%2280%22 y=%2250%22 text-anchor=%22middle%22 fill=%22oklch(0.65%200.008%20285)%22 font-size=%2212%22>Audio</text></svg>'">
            ${video.duration ? `<span class="duration">${formatDuration(video.duration)}</span>` : ''}
        </div>
        <div class="video-info">
            <div class="title">${escapeHtml(video.title)}</div>
            <div class="channel">${escapeHtml(video.channel)}</div>
            ${(video.artist || video.album) ? `<div class="video-meta-badges">
                ${video.artist ? `<span class="meta-badge">${escapeHtml(video.artist)}</span>` : ''}
                ${video.album ? `<span class="meta-badge">${escapeHtml(video.album)}</span>` : ''}
            </div>` : ''}
            ${video.view_count ? `<div class="meta"><span>${formatViews(video.view_count)}</span></div>` : ''}
        </div>
        <div class="video-actions">
            <button class="btn-download" data-url="${video.url}" data-title="${escapeAttr(video.title)}" title="${t('downloadAudio')}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                <span>${t('download')}</span>
            </button>
        </div>
    `;
    return card;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function escapeAttr(str) {
    return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function createSkeletonCard() {
    const card = document.createElement('div');
    card.className = 'video-card skeleton';
    card.innerHTML = `
        <div class="video-thumb"></div>
        <div class="video-info">
            <div class="title"></div>
            <div class="channel"></div>
            <div class="video-meta-badges">
                <div class="meta-badge"></div>
                <div class="meta-badge"></div>
            </div>
            <div class="meta"></div>
        </div>
        <div class="video-actions">
            <div class="btn-download"></div>
        </div>
    `;
    return card;
}

function showSkeleton(count = 3) {
    emptyState.classList.add('hidden');
    resultsSection.classList.remove('hidden');
    resultsList.innerHTML = '';
    resultsHeader.querySelector('.count').textContent = t('searching');
    for (let i = 0; i < count; i++) {
        resultsList.appendChild(createSkeletonCard());
    }
}

function showLoading(show) {
    loadingEl.classList.toggle('hidden', !show);
}

function showResults(videos) {
    emptyState.classList.add('hidden');
    resultsSection.classList.remove('hidden');
    resultsList.innerHTML = '';
    resultsHeader.querySelector('.count').textContent = t('resultsCount', videos.length);

    videos.forEach((video, index) => {
        const card = renderVideoCard(video);
        // Set initial state for staggered animation
        card.style.opacity = '0';
        resultsList.appendChild(card);
        requestAnimationFrame(() => {
            card.style.animation = `fadeInCard 0.2s var(--ease-out-quart) ${index * 50}ms forwards`;
        });
    });
}

function showEmpty() {
    resultsSection.classList.add('hidden');
    emptyState.classList.remove('hidden');
}

// ── Download Flow ────────────────────────────────────────────────
async function startDownload(btn, url, title) {
    btn.disabled = true;
    btn.classList.add('downloading');
    btn.querySelector('span').textContent = t('preparing');

    // Add progress bar
    const card = btn.closest('.video-card');
    let progressBar = card.querySelector('.progress-bar');
    if (!progressBar) {
        progressBar = document.createElement('div');
        progressBar.className = 'progress-bar';
        progressBar.innerHTML = `<div class="progress-fill" style="width:0%"></div>`;
        card.appendChild(progressBar);
    }
    const fill = progressBar.querySelector('.progress-fill');
    fill.style.width = '0%';

    try {
        const { task_id } = await apiDownload(url, title);

        // Update button text
        btn.querySelector('span').textContent = t('downloading');

        // Poll progress
        const interval = setInterval(async () => {
            try {
                const progress = await apiProgress(task_id);
                if (!progress) return;

                if (progress.status === 'downloading') {
                    fill.style.width = `${progress.percent}%`;
                } else if (progress.status === 'processing') {
                    fill.style.width = '100%';
                } else if (progress.status === 'done') {
                    clearInterval(interval);
                    state.activeDownloads.delete(task_id);

                    fill.style.width = '100%';
                    fill.style.background = 'var(--color-success)';

                    showToast(t('fileSaved', progress.filename));

                    btn.classList.remove('downloading');
                    btn.classList.add('done');
                    btn.querySelector('span').textContent = t('done');
                    btn.disabled = true;

                    // Reset button after a delay
                    setTimeout(() => {
                        btn.classList.remove('done');
                        btn.querySelector('span').textContent = t('download');
                        btn.disabled = false;
                        btn.onclick = () => startDownload(btn, url, title);
                        progressBar.remove();
                        // Cleanup task on backend
                        fetch(`/api/tasks/${task_id}`, { method: 'DELETE' });
                    }, 3000);
                } else if (progress.status === 'error') {
                    clearInterval(interval);
                    state.activeDownloads.delete(task_id);
                    throw new Error(progress.error || 'Erro desconhecido');
                }
            } catch (err) {
                clearInterval(interval);
                state.activeDownloads.delete(task_id);
                btn.classList.remove('downloading');
                btn.classList.add('error');
                btn.querySelector('span').textContent = t('error');
                btn.disabled = false;
                showToast(err.message, 'error');

                setTimeout(() => {
                    btn.classList.remove('error');
                    btn.querySelector('span').textContent = t('retry');
                    btn.onclick = () => startDownload(btn, url, title);
                    progressBar?.remove();
                }, 4000);
            }
        }, 500);

        state.activeDownloads.set(task_id, interval);
    } catch (err) {
        btn.classList.remove('downloading');
        btn.classList.add('error');
        btn.querySelector('span').textContent = t('error');
        btn.disabled = false;
        showToast(err.message, 'error');

        setTimeout(() => {
            btn.classList.remove('error');
            btn.querySelector('span').textContent = t('retry');
            btn.onclick = () => startDownload(btn, url, title);
            progressBar?.remove();
        }, 4000);
    }
}

// ── Event Handlers ───────────────────────────────────────────────
async function handleSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    searchBtn.disabled = true;
    searchBtn.querySelector('span').textContent = t('searching');
    showLoading(true);
    showSkeleton(3); // Show skeleton cards instead of hiding results

    try {
        const data = await apiSearch(query);
        showLoading(false);

        if (data.results && data.results.length > 0) {
            showResults(data.results);
        } else {
            showEmpty();
        }
    } catch (err) {
        showLoading(false);
        showToast(err.message, 'error');
        showEmpty();
    } finally {
        searchBtn.disabled = false;
        searchBtn.querySelector('span').textContent = t('search');
    }
}

// Search click
searchBtn.addEventListener('click', handleSearch);

// Enter key
searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSearch();
});

// Download buttons (delegated)
resultsList.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn-download');
    if (!btn || btn.disabled) return;
    startDownload(btn, btn.dataset.url, btn.dataset.title);
});

// ── Cookie Management ──────────────────────────────────────────────
const settingsBtn = $('#settings-btn');
const settingsModal = $('#settings-modal');
const modalClose = $('#modal-close');
const modalOverlay = settingsModal?.querySelector('.modal-overlay');
const cookieStatus = $('#cookie-status');
const cookieFileInput = $('#cookie-file-input');
const deleteCookiesBtn = $('#delete-cookies-btn');
const cookiesIndicator = $('#cookies-indicator');

async function checkCookiesStatus() {
    try {
        const res = await fetch('/api/cookies/status');
        const data = await res.json();

        if (data.has_cookies) {
            cookieStatus.className = 'cookie-status active';
            cookieStatus.querySelector('.status-text').textContent = t('cookiesLoaded');
            deleteCookiesBtn.classList.remove('hidden');
            cookiesIndicator.classList.remove('hidden', 'warning');
        } else {
            cookieStatus.className = 'cookie-status inactive';
            cookieStatus.querySelector('.status-text').textContent = t('noCookies');
            deleteCookiesBtn.classList.add('hidden');
            cookiesIndicator.classList.remove('hidden');
            cookiesIndicator.classList.add('warning');
        }
    } catch {
        cookieStatus.className = 'cookie-status error';
        cookieStatus.querySelector('.status-text').textContent = t('cookiesError');
    }
}

function openSettingsModal() {
    lastFocusedElement = document.activeElement;
    settingsModal.classList.remove('hidden');
    // Focus the modal content
    const modalContent = settingsModal.querySelector('.modal-content');
    modalContent?.focus();
    checkCookiesStatus();
}

function closeSettingsModal() {
    settingsModal.classList.add('hidden');
    if (lastFocusedElement) lastFocusedElement.focus();
}

settingsBtn?.addEventListener('click', openSettingsModal);
modalClose?.addEventListener('click', closeSettingsModal);
modalOverlay?.addEventListener('click', closeSettingsModal);

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !settingsModal.classList.contains('hidden')) {
        closeSettingsModal();
    }
});

cookieFileInput?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/cookies/upload', {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();

        if (res.ok) {
            showToast(data.message || t('cookiesUpdated'));
            checkCookiesStatus();
        } else {
            showToast(data.detail || t('cookiesUploadError'), 'error');
        }
    } catch (err) {
        showToast(t('cookiesUploadError') + ': ' + err.message, 'error');
    }

    // Reset input so the same file can be re-uploaded
    cookieFileInput.value = '';
});

deleteCookiesBtn?.addEventListener('click', async () => {
    try {
        const res = await fetch('/api/cookies', { method: 'DELETE' });
        const data = await res.json();
        showToast(data.message || t('cookiesRemoved'));
        checkCookiesStatus();
    } catch (err) {
        showToast(t('cookiesRemoveError') + ': ' + err.message, 'error');
    }
});

// Check cookies on page load
checkCookiesStatus();

// ── Language Toggle ─────────────────────────────────────────────
$('#lang-toggle')?.addEventListener('click', () => {
    currentLocale = currentLocale === 'pt' ? 'en' : 'pt';
    localStorage.setItem('bp-locale', currentLocale);
    $('#current-lang').textContent = currentLocale.toUpperCase();
    applyTranslations();
});

// ── Init ───────────────────────────────────────────────────────
$('#current-lang').textContent = currentLocale.toUpperCase();
applyTranslations();

// Focus input on load
searchInput.focus();
