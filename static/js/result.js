document.addEventListener('DOMContentLoaded', function() {
    // Здесь будем получать и отображать результаты
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
});

function displayResults(results) {
    // Отображаем соответствующие пункты
    const matchingPoints = document.getElementById('matching-points');
    results.matching_points.forEach(point => {
        const p = document.createElement('p');
        p.className = 'match';
        p.textContent = point;
        matchingPoints.appendChild(p);
    });

    // Отображаем несоответствия
    const discrepancies = document.getElementById('discrepancies');
    results.discrepancies.forEach(point => {
        const p = document.createElement('p');
        p.className = 'discrepancy';
        p.textContent = point;
        discrepancies.appendChild(p);
    });

    // Отображаем рекомендации
    const recommendations = document.getElementById('recommendations');
    results.recommendations.forEach(point => {
        const p = document.createElement('p');
        p.className = 'recommendation';
        p.textContent = point;
        recommendations.appendChild(p);
    });
} 