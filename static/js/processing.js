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
            const resultCardHeader = resultCard.querySelector('h1');
            const complianceInfo = document.querySelector('.compliance-info');

            switch (data.status) {
                case 'processing':
                    progressText.textContent = `Обработка...`;
                    responseContent.textContent = 'Ваш отчет в процессе обработки.';
                    resultCardHeader.textContent = 'Идет составление отчета';
                    downloadButton.style.display = 'none';
                    viewErrorsButton.style.display = 'none';
                    if (complianceInfo) complianceInfo.style.display = 'none';
                    setTimeout(checkStatus, 1000);
                    break;

                case 'completed':
                    resultCardHeader.textContent = 'Составление отчета завершено!';
                    progressText.textContent = 'Обработка завершена!';
                    responseContent.textContent = 'Ваш отчет готов к просмотру!';
                    downloadButton.style.display = 'block';
                    viewErrorsButton.style.display = 'flex';
                    downloadButton.disabled = false;
                    viewErrorsButton.disabled = false;

                    // Добавляем информацию о соответствии
                    if (complianceInfo) {
                        complianceInfo.style.display = 'block';
                        complianceInfo.innerHTML = `
                            <div class="compliance-meter">
                                <div class="meter-bar" style="width: ${data.total_compliance}%"></div>
                                <span class="meter-text">${data.total_compliance}% соответствия</span>
                            </div>
                            <p class="conclusion">${data.conclusion}</p>
                        `;
                    }
                    break;

                case 'error':
                    resultCardHeader.textContent = 'Ошибка при составлении отчета';
                    responseContent.textContent = 'Ошибка создания отчета';
                    downloadButton.style.display = 'none';
                    viewErrorsButton.style.display = 'none';
                    if (complianceInfo) complianceInfo.style.display = 'none';
                    break;

                default:
                    progressText.textContent = 'Неизвестный статус обработки';
                    resultCardHeader.textContent = 'Неизвестный статус';
                    break;
            }
        } catch (error) {
            console.error('Ошибка при проверке статуса:', error);
            const responseContent = document.querySelector('.response-content');
            const resultCardHeader = document.querySelector('.result-card h1');
            responseContent.textContent = 'Ошибка при проверке статуса обработки';
            resultCardHeader.textContent = 'Ошибка при обработке';
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
            const response = await fetch(`/status/${sessionId}`);
            if (!response.ok) throw new Error('Ошибка при получении отчета');
            const data = await response.json();

            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="search-container">
                        <h3>Интерактивный поиск</h3>
                        <div class="search-input-container">
                            <input type="text" class="search-input" placeholder="Например: Объяснить несоответствие">
                            <button class="search-button">Найти</button>
                        </div>
                    </div>

                    <div class="modal-main-content">
                        <div class="tabs">
                            <button class="tab-button active" data-tab="basic">Базовый отчет</button>
                            <button class="tab-button" data-tab="extended">Расширенный отчет</button>
                        </div>

                        <div class="tab-content active" data-tab="basic">
                            <h2>Отчет об ошибках</h2>
                            <div class="errors-list">
                                ${data.report ? data.report.map(item => `
                                    <div class="error-item"
                                         data-content="${item.Требование.toLowerCase()} ${item.Статус.toLowerCase()} ${item.Критичность.toLowerCase()} ${item.Анализ.toLowerCase()}"
                                         data-status="${item.Статус === 'соответствует ТЗ' ? 'success' : 'error'}">
                                        <div class="error-header">
                                            <div class="error-main-info">
                                                <h3>${item.Требование}</h3>
                                                <p class="status ${item.Статус === 'соответствует ТЗ' ? 'success' : 'error'}">
                                                    Статус: ${item.Статус}
                                                </p>
                                            </div>
                                            <button class="toggle-details">Подробнее ▼</button>
                                        </div>
                                        <div class="error-details" style="display:none">
                                            <p><strong>Критичность:</strong> ${item.Критичность}</p>
                                            <p><strong>Анализ:</strong> ${item.Анализ}</p>
                                            <div class="action-buttons">
                                                <button class="explain-button" data-requirement="${item.Требование}">
                                                    Пояснить
                                                </button>
                                                <button class="show-in-doc-button" data-requirement="${item.Требование}">
                                                    Показать в документации
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                `).join('') : '<p>Нет данных для отображения</p>'}
                            </div>
                        </div>

                        <div class="tab-content" data-tab="extended">
                            <h2>Расширенный отчет</h2>
                            ${data.extended_report ? `
                                <div class="compliance-summary">
                                    <h3>Общее соответствие: ${data.total_compliance}%</h3>
                                    <p>${data.conclusion}</p>
                                </div>
                                <div class="extended-list">
                                    ${data.extended_report.map(item => `
                                        <div class="extended-item">
                                            <h3>${item.Требование}</h3>
                                            <div class="compliance-meter">
                                                <div class="meter-bar" style="width: ${item.Соответствие.replace('%', '')}%"></div>
                                                <span class="meter-text">${item.Соответствие}</span>
                                            </div>
                                            <p><strong>Статус:</strong> ${item.Статус}</p>
                                            <p><strong>Детали:</strong> ${item.Детали}</p>
                                            <button class="explain-button" data-requirement="${item.Требование}">
                                                Детальный анализ
                                            </button>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : '<p>Нет данных для отображения</p>'}
                        </div>
                    </div>

                    <button class="close-button">Закрыть</button>
                </div>
            `;

            document.body.appendChild(modal);

            // Создаем отдельное модальное окно для документации
            const docModal = document.createElement('div');
            docModal.className = 'doc-modal';
            docModal.style.display = 'none';
            docModal.innerHTML = `
                <div class="doc-modal-content">
                    <div class="doc-modal-header">
                        <h3>Найдено в документации</h3>
                        <button class="close-doc-modal">×</button>
                    </div>
                    <div class="doc-modal-body">
                        <div class="doc-context"></div>
                    </div>
                </div>
            `;
            document.body.appendChild(docModal);

            // Добавляем обработчики для переключения вкладок
            const tabButtons = modal.querySelectorAll('.tab-button');
            const tabContents = modal.querySelectorAll('.tab-content');

            tabButtons.forEach(button => {
                button.addEventListener('click', () => {
                    // Убираем активный класс у всех кнопок и контента
                    tabButtons.forEach(btn => btn.classList.remove('active'));
                    tabContents.forEach(content => content.classList.remove('active'));

                    // Добавляем активный класс выбранной кнопке и соответствующему контенту
                    button.classList.add('active');
                    const tabName = button.getAttribute('data-tab');
                    modal.querySelector(`.tab-content[data-tab="${tabName}"]`).classList.add('active');
                });
            });

            // Добавляем функциональность поиска
            const searchInput = modal.querySelector('.search-input');
            const searchButton = modal.querySelector('.search-button');
            const errorItems = modal.querySelectorAll('.error-item');
            const extendedItems = modal.querySelectorAll('.extended-item');

            function performSearch() {
                const searchTerm = searchInput.value.toLowerCase();
                
                // Сбрасываем подсветку и видимость
                errorItems.forEach(item => {
                    item.classList.remove('highlight-section');
                    item.style.display = 'block';
                });
                extendedItems.forEach(item => {
                    item.classList.remove('highlight-section');
                    item.style.display = 'block';
                });
                
                if (searchTerm.length < 2) {
                    alert('Введите минимум 2 символа для поиска');
                    return;
                }
                
                let foundItems = false;
                
                // Поиск по всем элементам
                [...errorItems, ...extendedItems].forEach(item => {
                    const content = item.getAttribute('data-content') || '';
                    const requirement = item.querySelector('h3')?.textContent.toLowerCase() || '';
                    const status = item.querySelector('.status')?.textContent.toLowerCase() || '';
                    const details = item.querySelector('.error-details')?.textContent.toLowerCase() || '';
                    
                    // Проверяем совпадение по всем полям
                    const matches = content.includes(searchTerm) || 
                                  requirement.includes(searchTerm) || 
                                  status.includes(searchTerm) || 
                                  details.includes(searchTerm);
                    
                    if (matches) {
                        foundItems = true;
                        item.classList.add('highlight-section');
                        item.style.display = 'block';
                        
                        // Если это элемент с деталями, показываем их
                        const detailsElement = item.querySelector('.error-details');
                        if (detailsElement) {
                            detailsElement.style.display = 'block';
                        }
                    } else {
                        item.style.display = 'none';
                    }
                });
                
                if (!foundItems) {
                    alert('По вашему запросу ничего не найдено');
                }
            }
            
            // Обработчики событий для поиска
            searchButton.addEventListener('click', performSearch);
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    performSearch();
                }
            });

            // Остальные обработчики (аналогично предыдущей версии)
            modal.querySelectorAll('.toggle-details').forEach(button => {
                button.addEventListener('click', function() {
                    const card = this.closest('.error-item');
                    const details = card.querySelector('.error-details');
                    const isHidden = details.style.display === 'none';

                    details.style.display = isHidden ? 'block' : 'none';
                    this.textContent = isHidden ? 'Свернуть ▲' : 'Подробнее ▼';

                    if (isHidden) {
                        setTimeout(() => {
                            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        }, 50);
                    }
                });
            });

            // Обработчик кнопки "Пояснить" для обоих вкладок
            modal.querySelectorAll('.explain-button').forEach(button => {
                button.addEventListener('click', async function() {
                    const requirement = this.getAttribute('data-requirement');
                    const card = this.closest('.error-item') || this.closest('.extended-item');

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

                        const explanationBox = document.createElement('div');
                        explanationBox.className = 'detailed-explanation';
                        explanationBox.innerHTML = `
                            <h4>🔍 Детальный анализ:</h4>
                            ${formatExplanation(data.explanation)}
                            <button class="close-explanation">Скрыть</button>
                        `;

                        card.appendChild(explanationBox);

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

            // Обработчик кнопки "Показать в документации"
            modal.querySelectorAll('.show-in-doc-button').forEach(button => {
                button.addEventListener('click', async function() {
                    const requirement = this.getAttribute('data-requirement');
                    const docContext = docModal.querySelector('.doc-context');

                    const loader = document.createElement('div');
                    loader.className = 'doc-search-loading';
                    loader.textContent = 'Ищем в документации...';
                    docContext.appendChild(loader);

                    try {
                        const response = await fetch('/find-in-document', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                requirement: requirement,
                                session_id: sessionId
                            })
                        });
                        const data = await response.json();

                        if (!data.found) {
                            alert('Текст не найден в документации');
                            return;
                        }

                        docContext.innerHTML = data.results[0].content;
                        docModal.style.display = 'flex';

                        // Добавляем обработчик для кнопки закрытия
                        docModal.querySelector('.close-doc-modal').addEventListener('click', () => {
                            docModal.style.display = 'none';
                        });

                        // Закрытие по клику вне окна
                        docModal.addEventListener('click', (e) => {
                            if (e.target === docModal) {
                                docModal.style.display = 'none';
                            }
                        });

                    } catch (error) {
                        alert('Ошибка поиска');
                        console.error(error);
                    } finally {
                        loader.remove();
                    }
                });
            });

            // Обработчики закрытия
            modal.querySelector('.close-button').addEventListener('click', () => {
                modal.remove();
            });

            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });

            // Функция форматирования пояснений
            function formatExplanation(text) {
                return text
                    .replace(/- Несоответствие:/g, '<strong>🚨 Несоответствие:</strong>')
                    .replace(/- Причина:/g, '<strong>📌 Причина:</strong>')
                    .replace(/- Рекомендация:/g, '<strong>💡 Рекомендация:</strong>')
                    .replace(/- Критичность:/g, '<strong>⚠️ Критичность:</strong>')
                    .replace(/\n/g, '<br>');
            }

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