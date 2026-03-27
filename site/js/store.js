// Alpine.js reactive store for Conlexa frontend
document.addEventListener('alpine:init', () => {
    Alpine.store('conlexa', {
        // Reactive state
        filters: {
            part_of_speech: '',
            language_code: '',
        },
        languages: [],
        isLoading: false,
        
        // Initialize store
        init() {
            // Load languages on store initialization
            this.loadLanguages();
        },
        
        // Load all languages
        async loadLanguages() {
            this.isLoading = true;
            try {
                const langs = await fetchLanguages();
                this.languages = langs;
            } catch (error) {
                console.error('Failed to load languages:', error);
            } finally {
                this.isLoading = false;
            }
        },
        
        // Update filter
        setFilter(key, value) {
            this.filters[key] = value;
        },
        
        // Clear all filters
        clearFilters() {
            this.filters = {
                part_of_speech: '',
                language_code: '',
            };
        },
    });
});