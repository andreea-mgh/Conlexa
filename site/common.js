async function getPartsOfSpeechForLanguage(langCode) {
    if (!langCode) return [];
    const res = await fetch(`/api/langs/${encodeURIComponent(langCode)}`);
    if (!res.ok) return [];
    const langData = await res.json();
    return langData.parts_of_speech || [];
}

async function updatePartsOfSpeechSelect(langCode) {
    const posSelect = document.querySelector('#edit-form select[name="pos"]');
    if (!posSelect) return;

    const partsOfSpeech = await getPartsOfSpeechForLanguage(langCode);
    const currentValue = posSelect.value;

    // Clear all existing options
    posSelect.innerHTML = '';

    // Add blank option (since allowBlank is true for pos select)
    const blankOpt = document.createElement('option');
    blankOpt.value = '';
    blankOpt.textContent = '—';
    posSelect.appendChild(blankOpt);

    // Add new options
    partsOfSpeech.forEach(pos => {
        const opt = document.createElement('option');
        opt.value = pos.code;
        opt.textContent = pos.code;
        posSelect.appendChild(opt);
    });

    // Restore previous value if it exists in new options
    if (currentValue && partsOfSpeech.some(pos => pos.code === currentValue)) {
        posSelect.value = currentValue;
    } else {
        posSelect.value = '';
    }
}