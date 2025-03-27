function processComparisonResults(results) {
    const resultContainer = document.createElement('div');
    resultContainer.className = 'result-card';

    const sections = {
        matches: createResultSection('Совпадения'),
        discrepancies: createResultSection('Расхождения'),
        recommendations: createResultSection('Рекомендации')
    };

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

    Object.values(sections).forEach(section => {
        resultContainer.appendChild(section);
    });

    const backButton = document.createElement('button');
    backButton.className = 'back-button';
    backButton.textContent = 'Назад';
    backButton.onclick = () => {
        resultContainer.remove();
        document.querySelector('.container').style.display = 'block';
    };
    resultContainer.appendChild(backButton);

    document.querySelector('.container').style.display = 'none';
    document.body.appendChild(resultContainer);
}

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
    
    const resultCard = document.querySelector('.result-card');
    if (resultCard) {
        resultCard.appendChild(progressText);
    }

    const sessionId = localStorage.getItem('processing_session_id');
    if (!sessionId) {
        window.location.href = '/';
        return;
    }

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

    async function checkStatus() {
        try {
            const response = await fetch(`/status/${sessionId}`);
            const data = await response.json();

            switch (data.status) {
                case 'processing':
                    progressText.textContent = `Обработка: ${data.progress}%`;
                    downloadButton.style.display = 'none';
                    viewErrorsButton.style.display = 'none';
                    setTimeout(checkStatus, 1000);
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

    downloadButton.addEventListener('click', async function() {
        try {
            window.location.href = `/download-report/${sessionId}`;
        } catch (error) {
            alert('Ошибка при скачивании отчета');
            console.error('Ошибка:', error);
        }
    });

    viewErrorsButton.addEventListener('click', async function() {
        try {
            const response = await fetch(`/errors/${sessionId}`);
            if (!response.ok) {
                throw new Error('Ошибка при получении отчета об ошибках');
            }
            const data = await response.json();
            
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="search-container">
                        <h3>Интерактивный поиск</h3>
                        <div class="search-input-container">
                            <input type="text" class="search-input" placeholder="Например: Объяснить несоответствие в обработке изображений">
                            <button class="search-button">Найти</button>
                        </div>
                    </div>
                    <h2>Отчет об ошибках</h2>
                    <div class="errors-list">
                        ${data.errors.map(error => `
                            <div class="error-item" 
                                 data-content="${error.requirement.toLowerCase()} ${error.status.toLowerCase()} ${error.criticality.toLowerCase()} ${error.analysis.toLowerCase()}"
                                 data-section="${error.section || 'Общие требования'}"
                                 data-status="${error.status === 'соответствует ТЗ' ? 'success' : 'error'}">
                                <h3>${error.requirement}</h3>
                                <p class="status ${error.status === 'соответствует ТЗ' ? 'success' : 'error'}">
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
            
            // Создаем боковую панель с пояснениями
            const explanationPanel = document.createElement('div');
            explanationPanel.className = 'explanation-panel';
            explanationPanel.innerHTML = `
                <button class="close-panel">×</button>
                <h3>Пояснение</h3>
                <div class="explanation-content">
                    <div class="explanation-text"></div>
                    <div class="reference-links"></div>
                </div>
            `;
            document.body.appendChild(explanationPanel);
            
            // Добавляем функциональность поиска
            const searchInput = modal.querySelector('.search-input');
            const searchButton = modal.querySelector('.search-button');
            const errorItems = modal.querySelectorAll('.error-item');
            
            function performSearch() {
                const searchTerm = searchInput.value.toLowerCase();
                
                // Сбрасываем подсветку
                errorItems.forEach(item => {
                    item.classList.remove('highlight-section');
                    item.style.display = 'block';
                });
                
                if (searchTerm.length < 3) {
                    alert('Введите минимум 3 символа для поиска');
                    return;
                }
                
                let foundItems = false;
                
                // Обрабатываем интерактивный запрос
                if (searchTerm.includes('объяснить') || searchTerm.includes('показать')) {
                    // Извлекаем ключевые слова из запроса
                    const keywords = searchTerm
                        .replace(/^(объяснить|показать)/, '')
                        .trim()
                        .split(' ')
                        .filter(word => word.length > 2);
                    
                    errorItems.forEach(item => {
                        const content = item.getAttribute('data-content');
                        const itemSection = item.getAttribute('data-section');
                        
                        // Проверяем совпадение по всем ключевым словам
                        const matches = keywords.some(keyword => {
                            const contentMatch = content.includes(keyword);
                            const sectionMatch = itemSection.toLowerCase().includes(keyword);
                            return contentMatch || sectionMatch;
                        });
                        
                        if (matches) {
                            foundItems = true;
                            item.classList.add('highlight-section');
                            item.classList.add(item.getAttribute('data-status'));
                            
                            // Показываем пояснение в боковой панели
                            const explanationText = item.querySelector('p:last-child').textContent;
                            const sectionRef = item.getAttribute('data-section');
                            
                            // Обновляем содержимое боковой панели
                            const explanationPanelText = explanationPanel.querySelector('.explanation-text');
                            const referenceLinks = explanationPanel.querySelector('.reference-links');
                            
                            // Добавляем новый результат, сохраняя предыдущие
                            const newExplanation = document.createElement('div');
                            newExplanation.className = 'explanation-item';
                            newExplanation.innerHTML = `
                                <h4>${item.querySelector('h3').textContent}</h4>
                                <p>${explanationText}</p>
                                <a href="#" class="reference-link" data-section="${sectionRef}">
                                    ТЗ, ${sectionRef}
                                </a>
                            `;
                            
                            explanationPanelText.appendChild(newExplanation);
                            
                            // Показываем боковую панель
                            explanationPanel.classList.add('active');
                        } else {
                            item.style.display = 'none';
                        }
                    });
                } else {
                    // Обычный поиск по всем полям
                    errorItems.forEach(item => {
                        const content = item.getAttribute('data-content');
                        const itemSection = item.getAttribute('data-section');
                        const matches = content.includes(searchTerm) || itemSection.toLowerCase().includes(searchTerm);
                        
                        if (matches) {
                            foundItems = true;
                            item.classList.add('highlight-section');
                            item.classList.add(item.getAttribute('data-status'));
                            
                            // Показываем пояснение в боковой панели
                            const explanationText = item.querySelector('p:last-child').textContent;
                            const sectionRef = item.getAttribute('data-section');
                            
                            // Обновляем содержимое боковой панели
                            const explanationPanelText = explanationPanel.querySelector('.explanation-text');
                            const referenceLinks = explanationPanel.querySelector('.reference-links');
                            
                            // Добавляем новый результат, сохраняя предыдущие
                            const newExplanation = document.createElement('div');
                            newExplanation.className = 'explanation-item';
                            newExplanation.innerHTML = `
                                <h4>${item.querySelector('h3').textContent}</h4>
                                <p>${explanationText}</p>
                                <a href="#" class="reference-link" data-section="${sectionRef}">
                                    ТЗ, ${sectionRef}
                                </a>
                            `;
                            
                            explanationPanelText.appendChild(newExplanation);
                            
                            // Показываем боковую панель
                            explanationPanel.classList.add('active');
                        } else {
                            item.style.display = 'none';
                        }
                    });
                }
                
                if (!foundItems) {
                    alert('По вашему запросу ничего не найдено');
                }
            }
            
            // Обработчики событий
            searchButton.addEventListener('click', performSearch);
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    performSearch();
                }
            });
            
            // Обработчики закрытия
            modal.querySelector('.close-button').addEventListener('click', () => {
                modal.remove();
                explanationPanel.remove();
            });
            
            explanationPanel.querySelector('.close-panel').addEventListener('click', () => {
                explanationPanel.classList.remove('active');
            });
            
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                    explanationPanel.remove();
                }
            });
            
            // Обработчик клика по ссылкам в боковой панели
            explanationPanel.addEventListener('click', (e) => {
                if (e.target.classList.contains('reference-link')) {
                    e.preventDefault();
                    const section = e.target.getAttribute('data-section');
                    searchInput.value = `Показать раздел ${section}`;
                    performSearch();
                }
            });
            
        } catch (error) {
            alert('Ошибка при получении отчета об ошибках');
            console.error('Ошибка:', error);
        }
    });

    checkStatus();

    window.addEventListener('beforeunload', function() {
        localStorage.removeItem('processing_session_id');
    });
});