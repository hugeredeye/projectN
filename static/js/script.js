let tzFile = null;
let docFile = null;
let fileList = null;
let uploadedFiles = null;
let compareButton = null;
let errorReport = null;

document.addEventListener('DOMContentLoaded', function() {
    const tzInput = document.getElementById('tz-input');
    const docInput = document.getElementById('doc-input');
    compareButton = document.getElementById('compare-button');
    uploadedFiles = document.getElementById('uploaded-files');
    fileList = document.getElementById('file-list');
    errorReport = document.getElementById('error-report');

    tzInput.addEventListener('change', (e) => handleFileSelect(e, 'tz'));
    docInput.addEventListener('change', (e) => handleFileSelect(e, 'doc'));
    compareButton.addEventListener('click', handleCompare);

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

    // Инициализация кнопки для отображения изображения
    const imageToggleButton = document.getElementById('image-toggle-button');
    const imageModal = document.getElementById('image-modal');

    if (!imageToggleButton || !imageModal) {
        console.error('Кнопка или модальное окно для изображения не найдены!');
    } else {
        // Показать изображение при клике на кнопку
        imageToggleButton.addEventListener('click', function() {
            imageModal.style.display = 'flex';
        });

        // Скрыть изображение при клике вне области изображения
        imageModal.addEventListener('click', function(e) {
            if (e.target === imageModal) {
                imageModal.style.display = 'none';
            }
        });
    }
});

function handleFileSelect(event, type) {
    const file = event.target.files[0];
    if (file) {
        console.log(`Выбран файл (${type}):`, file.name);
        if (type === 'tz') {
            tzFile = file;
        } else {
            docFile = file;
        }
        updateFileList();
    }
}

// Обновим функцию updateFileList
function updateFileList() {
    if (tzFile || docFile) {
        uploadedFiles.style.display = 'block';
        compareButton.style.display = (tzFile && docFile) ? 'flex' : 'none';
        showUploadedFiles();
    } else {
        uploadedFiles.style.display = 'none';
        compareButton.style.display = 'none';
    }
}

async function handleCompare() {
    console.log('Начало отправки файлов');
    if (!tzFile || !docFile) {
        console.error('Не выбраны оба файла');
        showError('Пожалуйста, загрузите оба файла');
        return;
    }

    const allowedTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ];
    if (!allowedTypes.includes(tzFile.type) || !allowedTypes.includes(docFile.type)) {
        showError('Пожалуйста, загрузите файлы в формате PDF, DOCX или TXT');
        return;
    }

    compareButton.disabled = true;
    compareButton.textContent = 'Отправка...';

    try {
        const formData = new FormData();
        formData.append('tz_file', tzFile);
        formData.append('project_file', docFile);

        const response = await fetch('/compare', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Ошибка при отправке файлов');
        }

        const data = await response.json();
        console.log('Ответ от сервера:', data);

        if (data.status === 'processing') {
            localStorage.setItem('processing_session_id', data.session_id);
            window.location.href = '/processing';
        } else {
            throw new Error(data.message || 'Произошла ошибка при загрузке файлов');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showError(error.message);
    } finally {
        compareButton.disabled = false;
        compareButton.textContent = 'Сравнение';
    }
}

function showError(message) {
    if (errorReport) {
        errorReport.querySelector('p').textContent = message;
        errorReport.style.display = 'block';
    }
}

function hideError() {
    if (errorReport) {
        errorReport.style.display = 'none';
    }
}

// Функция для экранирования HTML
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Функция для чтения DOCX файлов
async function readDocxFile(file) {
    try {
        // Используем mammoth.js для чтения DOCX с сохранением форматирования
        const mammoth = await import('https://cdn.jsdelivr.net/npm/mammoth@1.4.0/+esm');
        const arrayBuffer = await file.arrayBuffer();

        const result = await mammoth.convertToHtml({ arrayBuffer });
        return result.value; // Возвращаем HTML с форматированием
    } catch (error) {
        console.error('Ошибка чтения DOCX:', error);
        return 'Не удалось прочитать содержимое DOCX файла';
    }
}

// Функция для обработки markdown
async function processMarkdown(content) {
    try {
        // Используем marked.js для преобразования markdown в HTML
        const marked = await import('https://cdn.jsdelivr.net/npm/marked@4.0.0/+esm');
        return marked.parse(content);
    } catch (error) {
        console.error('Ошибка обработки markdown:', error);
        return content;
    }
}

// Обновим функцию showFileContent
async function showFileContent(file, fileName) {
    const modal = document.createElement('div');
    modal.className = 'file-modal';
    modal.innerHTML = `
        <div class="file-modal-content">
            <div class="file-modal-header">
                <h3>${fileName}</h3>
                <button class="close-modal">&times;</button>
            </div>
            <div class="file-content-container">
                <div class="file-content-loading">Загрузка...</div>
                <div class="file-content" style="display:none"></div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    const contentElement = modal.querySelector('.file-content');
    const loadingElement = modal.querySelector('.file-content-loading');

    // Закрытие по клику на кнопку
    modal.querySelector('.close-modal').addEventListener('click', () => {
        modal.remove();
    });

    // Закрытие по клику вне модального окна
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });

    try {
        let content = '';

        if (file.type === 'text/plain') {
            content = await file.text();
            // Проверяем, является ли файл markdown
            if (fileName.toLowerCase().endsWith('.md')) {
                content = await processMarkdown(content);
                contentElement.innerHTML = `<div class="markdown-content">${content}</div>`;
            } else {
                contentElement.innerHTML = `<pre class="text-content">${escapeHtml(content)}</pre>`;
            }
        } else if (file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
            content = await readDocxFile(file);
            contentElement.innerHTML = `<div class="docx-content">${content}</div>`;
        } else if (file.type === 'application/pdf') {
            // Для PDF создаем iframe
            const fileUrl = URL.createObjectURL(file);
            contentElement.innerHTML = `
                <iframe 
                    src="${fileUrl}" 
                    style="width: 100%; height: 100%; min-height: 500px; border: none;"
                    title="PDF Viewer">
                </iframe>
            `;
        } else {
            throw new Error('Неподдерживаемый формат файла');
        }

        loadingElement.style.display = 'none';
        contentElement.style.display = 'block';
    } catch (error) {
        console.error('Ошибка чтения файла:', error);
        loadingElement.textContent = 'Ошибка загрузки содержимого файла';
        loadingElement.style.color = 'var(--discrepancy-color)';
    }
}

// Обновим функцию showUploadedFiles
function showUploadedFiles() {
    const fileList = document.getElementById('file-list');
    fileList.innerHTML = '';

    if (tzFile) {
        const tzFileElement = document.createElement('div');
        tzFileElement.className = 'file-item';
        tzFileElement.innerHTML = `
            <span>${tzFile.name}</span>
            <button class="view-file-button" data-type="tz">Просмотреть</button>
        `;
        fileList.appendChild(tzFileElement);
    }

    if (docFile) {
        const docFileElement = document.createElement('div');
        docFileElement.className = 'file-item';
        docFileElement.innerHTML = `
            <span>${docFile.name}</span>
            <button class="view-file-button" data-type="doc">Просмотреть</button>
        `;
        fileList.appendChild(docFileElement);
    }

    // Обновляем обработчики для кнопок просмотра
    document.querySelectorAll('.view-file-button').forEach(button => {
        button.addEventListener('click', function() {
            const fileType = this.getAttribute('data-type');
            const file = fileType === 'tz' ? tzFile : docFile;
            showFileContent(file, file.name);
        });
    });
}
