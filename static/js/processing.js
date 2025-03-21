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

            switch (data.status) {
                case 'processing':
                    progressText.textContent = `Обработка...`;
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
                    progressText.textContent = `Ошибка: ${data.error_message}`;
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
                    <h2>Отчет об ошибках</h2>
                    <div class="errors-list">
                        ${data.errors.map(error => `
                            <div class="error-item">
                                <h3>${error.requirement}</h3>
                                <p class="status ${error.status === 'соответствует ТЗ' ? 'success' : 'error'}">
                                    Статус: ${error.status}
                                </p>
                                <p>Критичность: ${error.criticality}</p>
                                <p>Анализ: ${error.analysis}</p>
                                <button class="explain-button" data-requirement="${error.requirement}">Пояснить</button>
                            </div>
                        `).join('')}
                    </div>
                    <button class="close-button">Закрыть</button>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            modal.querySelector('.close-button').addEventListener('click', () => {
                modal.remove();
            });
            
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });

            // Добавляем обработчик для кнопок "Пояснить"
            modal.querySelectorAll('.explain-button').forEach(button => {
                button.addEventListener('click', async function() {
                    const requirement = this.getAttribute('data-requirement');
                    try {
                        const response = await fetch('/explain', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ requirement: requirement })
                        });
                        if (!response.ok) {
                            throw new Error('Ошибка при получении пояснения');
                        }
                        const data = await response.json();
                        alert(data.explanation);
                    } catch (error) {
                        alert('Ошибка при получении пояснения');
                        console.error('Ошибка:', error);
                    }
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