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
    
    // Проверяем, существует ли .result-card, прежде чем добавлять progressText
    const resultCard = document.querySelector('.result-card');
    if (resultCard) {
        resultCard.appendChild(progressText);
    }

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
                    progressText.textContent = `Обработка: ${data.progress}%`;
                    downloadButton.style.display = 'none';
                    viewErrorsButton.style.display = 'none';
                    setTimeout(checkStatus, 1000); // Проверяем каждую секунду
                    break;

                case 'completed':
                    progressText.textContent = 'Обработка завершена!';
                    downloadButton.style.display = 'block';
                    viewErrorsButton.style.display = 'flex';
                    downloadButton.disabled = false;
                    viewErrorsButton.disabled = false;
                    break;

                case 'error':
                    progressText.textContent = `Ошибка: ${data.error}`;
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
            downloadButton.disabled = true;
            downloadButton.textContent = 'Скачивание...';
            
            const response = await fetch(`/download-report/${sessionId}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ошибка при скачивании отчета');
            }
            
            const blob = await response.blob();
            if (blob.size === 0) {
                throw new Error('Получен пустой файл');
            }
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `report_${sessionId}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            downloadButton.textContent = 'Скачать отчет с исправлениями';
        } catch (error) {
            console.error('Ошибка:', error);
            alert('Ошибка при скачивании отчета: ' + error.message);
            downloadButton.textContent = 'Скачать отчет с исправлениями';
        } finally {
            downloadButton.disabled = false;
        }
    });

    // Обработчик кнопки просмотра ошибок
    viewErrorsButton.addEventListener('click', async function() {
        try {
            const response = await fetch(`/errors/${sessionId}`);
            if (!response.ok) {
                throw new Error('Ошибка при получении отчета об ошибках');
            }
            const data = await response.json();
            
            // Создаем модальное окно для отображения ошибок
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h2>Отчет об ошибках</h2>
                    <div class="errors-list">
                        ${data.errors.map(error => `
                            <div class="error-item">
                                <h3>${error.requirement}</h3>
                                <p class="status ${error.status === 'соответствует' ? 'success' : 'error'}">
                                    Статус: ${error.status}
                                </p>
                                <p>Критичность: ${error.criticality}</p>
                                <p>Анализ: ${error.analysis}</p>
                            </div>
                        `).join('')}
                    </div>
                    <button class="close-button">Закрыть</button>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Обработчик закрытия модального окна
            modal.querySelector('.close-button').addEventListener('click', () => {
                modal.remove();
            });
            
            // Закрытие по клику вне модального окна
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });
        } catch (error) {
            alert('Ошибка при получении отчета об ошибках');
            console.error('Ошибка:', error);
        }
    });

    // Начинаем проверку статуса
    checkStatus();

    // Очищаем session_id при уходе со страницы
    window.addEventListener('beforeunload', function() {
        localStorage.removeItem('processing_session_id');
    });
});