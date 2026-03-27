// Global utilities for Conlexa frontend
// HTML escaping (duplicated in dict.html, langs.html, ipa.html, word.html)
function esc(str) {
    if (!str) return '';
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// URL parameter parsing (duplicated in langs.html)
function getQueryParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

// Select element builder (duplicated in word.html)
function makeSelect(name, options, current, allowBlank = true) {
    const opts = options.map(o =>
        `<option value="${esc(o)}"${o === current ? ' selected' : ''}>${esc(o)}</option>`
    ).join('');
    return `<select name="${name}" class="edit-field">${allowBlank ? '<option value="">—</option>' : ''}${opts}</select>`;
}