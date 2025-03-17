// Функция для обработки результатов сравнения документов
function processComparisonResults(results) {
    const resultContainer = document.createElement('div');
    resultContainer.className = 'result-card';

    // Создаем секции для разных типов результатов
    const sections = {
        matches: createResultSection('Совпадения'),
        discrepancies: createResultSection('Расхождения'), 
        recommendations: createResultSection('Рекомендации')
    };

    // Добавляем результаты в соответствующие секции
    results.forEach(result => {
        const point = document.createElement('p');
        point.className = result.type;
        point.textContent = result.text;
        
        switch(result.type) {
            case 'match':
                sections.matches.querySelector('.points-list').appendChild(point);
                break;
            case 'discrepancy':
                sections.discrepancies.querySelector('.points-list').appendChild(point);
                break;
            case 'recommendation':
                sections.recommendations.querySelector('.points-list').appendChild(point);
                break;
        }
    });

    // Добавляем секции в контейнер
    Object.values(sections).forEach(section => {
        resultContainer.appendChild(section);
    });

    // Добавляем кнопку "Назад"
    const backButton = document.createElement('button');
    backButton.className = 'back-button';
    backButton.textContent = 'Назад';
    backButton.onclick = () => {
        resultContainer.remove();
        document.querySelector('.container').style.display = 'block';
    };
    resultContainer.appendChild(backButton);

    // Скрываем основной контейнер и показываем результаты
    document.querySelector('.container').style.display = 'none';
    document.body.appendChild(resultContainer);
}

// Вспомогательная функция для создания секции результатов
function createResultSection(title) {
    const section = document.createElement('div');
    section.className = 'result-section';
    
    const heading = document.createElement('h2');
    heading.textContent = title;
    
    const pointsList = document.createElement('div');
    pointsList.className = 'points-list';
    
    section.appendChild(heading);
    section.appendChild(pointsList);
    
    return section;
}

document.addEventListener('DOMContentLoaded', function() {
    const downloadButton = document.querySelector('.download-button');
    const viewErrorsButton = document.querySelector('.view-errors-button');
    const progressText = document.createElement('p');
    progressText.className = 'progress-text';
    document.querySelector('.result-card').appendChild(progressText);

    // Получаем session_id из localStorage
    const sessionId = localStorage.getItem('processing_session_id');
    if (!sessionId) {
        window.location.href = '/';
        return;
    }

    // Функция проверки статуса
    async function checkStatus() {
        try {
            const response = await fetch(`/status/${sessionId}`);
            const data = await response.json();

            switch (data.status) {
                case 'processing':
                    progressText.textContent = 'Обработка...';
                    downloadButton.style.display = 'none';
                    viewErrorsButton.style.display = 'none';
                    setTimeout(checkStatus, 1000); // Проверяем каждую секунду
                    break;

                case 'completed':
                    progressText.textContent = 'Обработка завершена!';
                    downloadButton.style.display = 'block';
                    viewErrorsButton.style.display = 'flex';
                    // Активируем кнопки
                    downloadButton.disabled = false;
                    viewErrorsButton.disabled = false;
                    break;

                case 'error':
                    progressText.textContent = `Ошибка: ${data.error_message || 'Неизвестная ошибка'}`;
                    downloadButton.style.display = 'none';
                    viewErrorsButton.style.display = 'none';
                    break;

                default:
                    progressText.textContent = 'Неизвестный статус обработки';
                    break;
            }
        } catch (error) {
            progressText.textContent = 'Ошибка при проверке статуса';
            console.error('Ошибка:', error);
        }
    }

    // Обработчик кнопки скачивания
    downloadButton.addEventListener('click', async function() {
        try {
            window.location.href = `/download-report/${sessionId}`;
        } catch (error) {
            alert('Ошибка при скачивании отчета');
            console.error('Ошибка:', error);
        }
    });

    // Обработчик кнопки просмотра ошибок
    viewErrorsButton.addEventListener('click', function() {
        window.location.href = '/errors';
    });

    // Начинаем проверку статуса
    checkStatus();

    // Очищаем session_id при уходе со страницы
    window.addEventListener('beforeunload', function() {
        localStorage.removeItem('processing_session_id');
    });
});