document.addEventListener('DOMContentLoaded', () => {
    const htmlElement = document.documentElement;
    const themeLinks = document.querySelectorAll('.dropdown-item[data-theme]');
    
    // Load saved theme
    const savedTheme = localStorage.getItem('plex-dlna-theme') || 'neon-cyber';
    applyTheme(savedTheme);
    
    themeLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const newTheme = e.target.getAttribute('data-theme');
            applyTheme(newTheme);
            localStorage.setItem('plex-dlna-theme', newTheme);
        });
    });
    
    function applyTheme(themeName) {
        htmlElement.setAttribute('data-theme', themeName);
        
        // Update active state in dropdown
        themeLinks.forEach(link => {
            if (link.getAttribute('data-theme') === themeName) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }
});
