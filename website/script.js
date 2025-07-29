let media = [];
let displayedMedia = [];

document.addEventListener('DOMContentLoaded', () => {
    fetch('../data/all_articles_output.json')
        .then(res => res.json())
        .then(data => {
            media = data.filter(article => article.title && article.summary_data);
            displayedMedia = [...media];
            renderMedia(displayedMedia);
            createSourceButtons(media); // Create dynamic source buttons

            // Attach live filtering for input fields
            document.querySelectorAll('[data-search]').forEach(input => {
                input.addEventListener('input', filterMedia);
            });
        })
        .catch(err => console.error('Error loading JSON:', err));
});

function createSourceButtons(data) {
    const uniqueSources = [...new Set(data.map(article => article.source).filter(Boolean))];
    const container = document.getElementById('source-button-container');

    uniqueSources.sort().forEach(source => {
        const button = document.createElement('button');
        button.className = 'filter';
        button.textContent = source;
        button.addEventListener('click', () => {
            displayedMedia = media.filter(article =>
                article.source.toLowerCase() === source.toLowerCase()
            );
            renderMedia(displayedMedia);
        });
        container.appendChild(button);
    });
}

function renderMedia(mediaArray) {
    const container = document.getElementById('media-container');
    container.innerHTML = '';

    mediaArray.forEach(article => {
        const sd = article.summary_data;
        const mediaDiv = document.createElement('div');
        mediaDiv.className = 'media';

        mediaDiv.innerHTML = `
            <h3 class="media-title">${article.title}</h3>
            <h4 class="media-source">${article.source}</h4>
            <div class="media-date">${article.date}</div>
            <div class="media-summary">${sd.summary}</div>
            <div class="media-category"><strong>Categories: </strong>${sd.category || 'N/A'}</div>
            <div class="media-product"><strong>Products: </strong>${sd.product || 'N/A'}</div>
            <div class="media-technology"><strong>Technologies: </strong>${sd.technology || 'N/A'}</div>
            <div class="media-tags"><strong>Tags: </strong>${sd.tags || 'N/A'}</div>
            <div class="media-companies"><strong>Companies: </strong>${sd.companies_mentioned || 'N/A'}</div>
            <div class="media-parent-companies"><strong>Parent companies: </strong>${sd.parent_companies_mentioned || 'N/A'}</div>
            <div class="media-countries"><strong>Countries: </strong>${sd.geography}</div>
            <a href="${article.url}" class="media-url" target="_blank">Read Article</a>
        `;
        container.appendChild(mediaDiv);
    });
}

function sortTitle(direction = 'asc') {
    displayedMedia.sort((a, b) => {
        const result = a.title.localeCompare(b.title);
        return direction === 'asc' ? result : -result;
    });
    renderMedia(displayedMedia);
}

function sortDate(direction = 'desc') {
    displayedMedia.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return direction === 'asc' ? dateA - dateB : dateB - dateA;
    });
    renderMedia(displayedMedia);
}


function removeSorting() {
    // Re-sort to original data order (filtered)
    displayedMedia = [...media];

    // Re-apply any active filters
    filterMedia();
}

function filterMedia() {
    const filters = {
        title: document.getElementById('search-title-bar').value.toLowerCase(),
        source: document.getElementById('search-source-bar').value.toLowerCase(),
        date: document.getElementById('search-date-bar').value.toLowerCase(),
        summary: document.getElementById('search-summary-bar').value.toLowerCase(),
        category: document.getElementById('search-category-bar').value.toLowerCase(),
        product: document.getElementById('search-product-bar').value.toLowerCase(),
        technology: document.getElementById('search-tech-bar').value.toLowerCase(),
        tags: document.getElementById('search-tags-bar').value.toLowerCase(),
        companies: document.getElementById('search-company-bar').value.toLowerCase(),
        parent_companies: document.getElementById('search-pcompany-bar').value.toLowerCase(),
        countries: document.getElementById('search-countries-bar').value.toLowerCase(),
    };

    displayedMedia = media.filter(article => {
        const sd = article.summary_data;
        return (
            article.title.toLowerCase().includes(filters.title) &&
            article.source.toLowerCase().includes(filters.source) &&
            (article.date || '').toLowerCase().includes(filters.date) &&
            (sd.summary || '').toLowerCase().includes(filters.summary) &&
            (sd.category || '').toLowerCase().includes(filters.category) &&
            (sd.product || '').toLowerCase().includes(filters.product) &&
            (sd.technology || '').toLowerCase().includes(filters.technology) &&
            (sd.tags || '').toString().toLowerCase().includes(filters.tags) &&
            (sd.companies_mentioned || '').toString().toLowerCase().includes(filters.companies) &&
            (sd.parent_companies || '').toString().toLowerCase().includes(filters.parent_companies) &&
            (sd.geography || '').toLowerCase().includes(filters.countries)
        );
    });

    renderMedia(displayedMedia);
}

function removeFilter() {
    displayedMedia = [...media];
    renderMedia(displayedMedia);
    document.querySelectorAll('[data-search]').forEach(input => input.value = '');
}
