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
        return;
    }

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

async function checkStatus() {
    try {
        const response = await fetch(`/status/${sessionId}`);
        const data = await response.json();

        // Получаем элементы
        const responseContent = document.querySelector('.response-content');
        const resultCard = document.querySelector('.result-card');
        const resultCardHeader = resultCard.querySelector('h1'); // Находим <h1> внутри .result-card

        switch (data.status) {
            case 'processing':
                progressText.textContent = `Обработка...`;
                responseContent.textContent = 'Ваш отчет в процессе обработки.';
                resultCardHeader.textContent = 'Идет составление отчета'; // Обновляем текст в <h1>
                downloadButton.style.display = 'none';
                viewErrorsButton.style.display = 'none';
                setTimeout(checkStatus, 1000);
                break;

            case 'completed':
                resultCardHeader.textContent = 'Составление отчета завершено!'; // Обновляем текст в <h1>
                progressText.textContent = 'Обработка завершена!';
                responseContent.textContent = 'Ваш отчет готов к просмотру!';
                downloadButton.style.display = 'block';
                viewErrorsButton.style.display = 'flex';
                downloadButton.disabled = false;
                viewErrorsButton.disabled = false;
                break;

            case 'error':
                resultCardHeader.textContent = 'Ошибка при составлении отчета'; // Обновляем текст в <h1>
                responseContent.textContent = 'Ошибка создания отчета';
                downloadButton.style.display = 'none';
                viewErrorsButton.style.display = 'none';
                break;

            default:
                progressText.textContent = 'Неизвестный статус обработки';
                resultCardHeader.textContent = 'Неизвестный статус'; // Обновляем текст в <h1>
                break;
        }
    } catch (error) {
        console.error('Ошибка при проверке статуса:', error);
        const responseContent = document.querySelector('.response-content');
        const resultCardHeader = document.querySelector('.result-card h1');
        responseContent.textContent = 'Ошибка при проверке статуса обработки';
        resultCardHeader.textContent = 'Ошибка при обработке'; // Обновляем текст в <h1> при ошибке
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
        if (!response.ok) throw new Error('Ошибка при получении отчета');
        const data = await response.json();

        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <!-- Существующий поиск (без изменений) -->
                <div class="search-container">
                    <h3>Интерактивный поиск</h3>
                    <div class="search-input-container">
                        <input type="text" class="search-input" placeholder="Например: Объяснить несоответствие">
                        <button class="search-button">Найти</button>
                    </div>
                </div>

                <h2>Отчет об ошибках</h2>
                <div class="errors-list">
                    ${data.errors.map(error => `
                        <!-- Обертка для карточки (сохраняем все data-атрибуты) -->
                        <div class="error-item"
                             data-content="${error.requirement.toLowerCase()} ${error.status.toLowerCase()} ${error.criticality.toLowerCase()} ${error.analysis.toLowerCase()}"
                             data-section="${error.section || 'Общие требования'}"
                             data-status="${error.status === 'соответствует ТЗ' ? 'success' : 'error'}">

                            <!-- Верхняя часть карточки (теперь с кнопкой) -->
                            <div class="error-header">
                                <div class="error-main-info">
                                    <h3>${error.requirement}</h3>
                                    <p class="status ${error.status === 'соответствует ТЗ' ? 'success' : 'error'}">
                                        Статус: ${error.status}
                                    </p>
                                </div>
                                <button class="toggle-details">Подробнее ▼</button>
                            </div>

                            <!-- Скрытая часть (появляется при клике) -->
                            <div class="error-details" style="display:none">
                                <p><strong>Критичность:</strong> ${error.criticality}</p>
                                <p><strong>Анализ:</strong> ${error.analysis}</p>
                                <div class="action-buttons">
                                    <button class="explain-button" data-requirement="${error.requirement}">
                                        Пояснить
                                    </button>
                                    <button class="show-in-doc-button" data-requirement="${error.requirement}">
                                        Показать в документации
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <button class="close-button">Закрыть</button>
            </div>
        `;

        document.body.appendChild(modal);

        // Боковая панель с пояснениями (существующий код)
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

        // 1. Обработчик кнопки "Подробнее" (НОВОЕ)
        modal.querySelectorAll('.toggle-details').forEach(button => {
            button.addEventListener('click', function() {
                const card = this.closest('.error-item');
                const details = card.querySelector('.error-details');
                const isHidden = details.style.display === 'none';

                details.style.display = isHidden ? 'block' : 'none';
                this.textContent = isHidden ? 'Свернуть ▲' : 'Подробнее ▼';

                // Прокрутка для плавного отображения
                if (isHidden) {
                    setTimeout(() => {
                        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }, 50);
                }
            });
        });

        // 2. Функция поиска (существующий код БЕЗ ИЗМЕНЕНИЙ)
        const searchInput = modal.querySelector('.search-input');
        const searchButton = modal.querySelector('.search-button');
        const errorItems = modal.querySelectorAll('.error-item');

        function performSearch() {
            const searchTerm = searchInput.value.toLowerCase();

            errorItems.forEach(item => {
                item.classList.remove('highlight-section');
                item.style.display = 'block';
            });

            if (searchTerm.length < 3) {
                alert('Введите минимум 3 символа для поиска');
                return;
            }

            let foundItems = false;

            if (searchTerm.includes('объяснить') || searchTerm.includes('показать')) {
                const keywords = searchTerm
                    .replace(/^(объяснить|показать)/, '')
                    .trim()
                    .split(' ')
                    .filter(word => word.length > 2);

                errorItems.forEach(item => {
                    const content = item.getAttribute('data-content');
                    const itemSection = item.getAttribute('data-section');

                    const matches = keywords.some(keyword => {
                        return content.includes(keyword) || itemSection.toLowerCase().includes(keyword);
                    });

                    if (matches) {
                        foundItems = true;
                        item.classList.add('highlight-section');
                        item.classList.add(item.getAttribute('data-status'));

                        // Автоматически раскрываем найденные карточки
                        item.querySelector('.error-details').style.display = 'block';
                        item.querySelector('.toggle-details').textContent = 'Свернуть ▲';
                    } else {
                        item.style.display = 'none';
                    }
                });
            } else {
                errorItems.forEach(item => {
                    const content = item.getAttribute('data-content');
                    const itemSection = item.getAttribute('data-section');
                    const matches = content.includes(searchTerm) || itemSection.toLowerCase().includes(searchTerm);

                    if (matches) {
                        foundItems = true;
                        item.classList.add('highlight-section');
                        item.classList.add(item.getAttribute('data-status'));
                    } else {
                        item.style.display = 'none';
                    }
                });
            }

            if (!foundItems) {
                alert('По вашему запросу ничего не найдено');
            }
        }

        // 3. Обработчики событий (существующий код)
        searchButton.addEventListener('click', performSearch);
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') performSearch();
        });

        // 4. Обработчики закрытия (существующий код)
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

        // 5. Обработчик пояснений
        // Заменяем только обработчик кнопки "Пояснить"
        modal.querySelectorAll('.explain-button').forEach(button => {
            button.addEventListener('click', async function() {
                const requirement = this.getAttribute('data-requirement');
                const card = this.closest('.error-item');

                // Добавляем индикатор загрузки
                const loadingIndicator = document.createElement('div');
                loadingIndicator.className = 'loading-explanation';
                loadingIndicator.textContent = 'Анализируем...';
                card.appendChild(loadingIndicator);

                try {
                    const response = await fetch('/detailed-explain', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            requirement: requirement,
                            session_id: sessionId
                        })
                    });

                    const data = await response.json();

                    // Создаем красивый вывод
                    const explanationBox = document.createElement('div');
                    explanationBox.className = 'detailed-explanation';
                    explanationBox.innerHTML = `
                        <h4>🔍 Детальный анализ:</h4>
                        ${formatExplanation(data.explanation)}
                        <button class="close-explanation">Скрыть</button>
                    `;

                    card.appendChild(explanationBox);

                    // Обработчик закрытия
                    explanationBox.querySelector('.close-explanation').addEventListener('click', () => {
                        explanationBox.remove();
                    });

                } catch (error) {
                    alert('Ошибка при анализе');
                    console.error(error);
                } finally {
                    loadingIndicator.remove();
                }
            });
        });

        // Форматирование текста от LLM
        function formatExplanation(text) {
            return text
                .replace(/- Несоответствие:/g, '<strong>🚨 Несоответствие:</strong>')
                .replace(/- Причина:/g, '<strong>📌 Причина:</strong>')
                .replace(/- Рекомендация:/g, '<strong>💡 Рекомендация:</strong>')
                .replace(/- Критичность:/g, '<strong>⚠️ Критичность:</strong>')
                .replace(/\n/g, '<br>');
        }

        // 6. Обработчик "Показать в документации" (заглушка)
        modal.querySelectorAll('.show-in-doc-button').forEach(button => {
            button.addEventListener('click', function() {
                alert('Функция "Показать в документации" будет реализована позже');
            });
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