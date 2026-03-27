// Global API client for Conlexa frontend

// Base fetch wrapper with error handling
async function fetchJSON(url, options = {}) {
    const res = await fetch(url, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...options.headers },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
}

// Language endpoints
async function fetchFilters() { 
    return fetchJSON('/api/filters'); 
}

async function fetchLanguages() { 
    const data = await fetchJSON('/api/langs');
    return data.langs || []; 
}

async function fetchLanguage(langCode) { 
    return fetchJSON(`/api/langs/${encodeURIComponent(langCode)}`); 
}

async function fetchPartsOfSpeech(langCode) {
    if (!langCode) return [];
    const lang = await fetchLanguage(langCode);
    return lang.parts_of_speech || [];
}

async function updateLanguage(langCode, data) {
    return fetchJSON(`/api/langs/${encodeURIComponent(langCode)}`, { 
        method: 'PUT', 
        body: JSON.stringify(data) 
    });
}

// Word endpoints
async function fetchWords(params = {}) {
    const queryParams = new URLSearchParams();
    if (params.part_of_speech) queryParams.set('part_of_speech', params.part_of_speech);
    if (params.language_code) queryParams.set('language_code', params.language_code);
    if (params.limit) queryParams.set('limit', params.limit);
    if (params.offset) queryParams.set('offset', params.offset);
    
    return fetchJSON(`/api/words?${queryParams}`);
}

async function fetchWord(id) { 
    return fetchJSON(`/api/words/${id}`); 
}

async function createWord(data) {
    return fetchJSON('/api/words', { 
        method: 'POST', 
        body: JSON.stringify(data) 
    });
}

async function updateWord(id, data) {
    return fetchJSON(`/api/words/${id}`, { 
        method: 'PUT', 
        body: JSON.stringify(data) 
    });
}

async function deleteWord(id) {
    const res = await fetch(`/api/words/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return { ok: true };
}

// Search
async function fetchSearchResults(query, target = 'words', filters = {}) {
    const params = new URLSearchParams({ query, target, limit: 100 });
    if (filters.part_of_speech) params.append('pos', filters.part_of_speech);
    if (filters.language_code) params.append('language_code', filters.language_code);
    
    const data = await fetchJSON(`/api/search?${params}`);
    return data.results || [];
}

// Default language
async function fetchDefaultLanguage() {
    const data = await fetchJSON('/api/default/lang');
    return data.language_code || '';
}

// Phonology
async function applyPhonology(word, langCode) {
    const params = new URLSearchParams({ word, lang_code: langCode });
    const data = await fetchJSON(`/api/phonology/apply?${params}`);
    return data.result || '';
}

// Parts of speech management
async function createPartOfSpeech(langCode, code, name_en) {
    return fetchJSON(`/api/langs/${encodeURIComponent(langCode)}/parts_of_speech`, {
        method: 'POST',
        body: JSON.stringify({ code, name_en }),
    });
}

async function deletePartOfSpeech(langCode, posCode) {
    const res = await fetch(`/api/langs/${encodeURIComponent(langCode)}/parts_of_speech/${encodeURIComponent(posCode)}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return { ok: true };
}