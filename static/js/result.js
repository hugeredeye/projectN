document.addEventListener('DOMContentLoaded', async function() {
    try {
        const response = await fetch('/results');
        const data = await response.json();
        displayResults(data);
    } catch (error) {
        console.error('Ошибка при получении результатов:', error);
        // Отображаем мок-данные в случае ошибки
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

    // Проверка на существование элементов
    if (!matchingPoints || !discrepancies || !recommendations) {
        console.error('Один из элементов для отображения результатов не найден');
        return;
    }

    // Отображаем соответствующие пункты
    results.matching_points.forEach(point => {
        const p = document.createElement('p');
        p.className = 'match';
        p.textContent = point;
        matchingPoints.appendChild(p);
    });

    // Отображаем несоответствия
    results.discrepancies.forEach(point => {
        const p = document.createElement('p');
        p.className = 'discrepancy';
        p.textContent = point;
        discrepancies.appendChild(p);
    });

    // Отображаем рекомендации
    results.recommendations.forEach(point => {
        const p = document.createElement('p');
        p.className = 'recommendation';
        p.textContent = point;
        recommendations.appendChild(p);
    });
}