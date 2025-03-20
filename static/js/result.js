document.addEventListener('DOMContentLoaded', async function() {
    // Инициализация переключения темы
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) {
        console.error('Кнопка переключения темы не найдена!');
    } else {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-theme');
            themeToggle.textContent = 'Светлая тема';
        } else {
            themeToggle.textContent = 'Темная тема';
        }

        themeToggle.addEventListener('click', function() {
            const body = document.body;
            if (body.classList.contains('dark-theme')) {
                body.classList.remove('dark-theme');
                themeToggle.textContent = 'Темная тема';
                localStorage.setItem('theme', 'light');
            } else {
                body.classList.add('dark-theme');
                themeToggle.textContent = 'Светлая тема';
                localStorage.setItem('theme', 'dark');
            }
        });
    }

    try {
        const response = await fetch('/results');
        const data = await response.json();
        displayResults(data);
    } catch (error) {
        console.error('Ошибка при получении результатов:', error);
        const mockResults = {
            matching_points: [
                "Пункт 1.1: Требования к авторизации полностью соответствуют",
                "Пункт 2.3: Интерфейс реализован согласно требованиям"
            ],
            discrepancies: [
                "Критическое: Пункт 1.2 - Используется MySQL вместо PostgreSQL",
                "Некритическое: Пункт 2.1 - Увеличен лимит загрузки файлов"
            ],
            recommendations: [
                "Рекомендуется перейти на PostgreSQL согласно ТЗ",
                "Необходимо добавить автоматическое сравнение документов"
            ]
        };
        displayResults(mockResults);
    }
});

function displayResults(results) {
    const matchingPoints = document.getElementById('matching-points');
    const discrepancies = document.getElementById('discrepancies');
    const recommendations = document.getElementById('recommendations');

    if (!matchingPoints || !discrepancies || !recommendations) {
        console.error('Один из элементов для отображения результатов не найден');
        return;
    }

    results.matching_points.forEach(point => {
        const p = document.createElement('p');
        p.className = 'match';
        p.textContent = point;
        matchingPoints.appendChild(p);
    });

    results.discrepancies.forEach(point => {
        const p = document.createElement('p');
        p.className = 'discrepancy';
        p.textContent = point;
        discrepancies.appendChild(p);
    });

    results.recommendations.forEach(point => {
        const p = document.createElement('p');
        p.className = 'recommendation';
        p.textContent = point;
        recommendations.appendChild(p);
    });
}