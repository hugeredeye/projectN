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
// Добавим новую функцию для отображения содержимого файла
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
                ${file.type === 'application/pdf' ?
                    '<div class="pdf-viewer-container"></div>' :
                    '<pre class="file-content">Загрузка...</pre>'
                }
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    const container = modal.querySelector('.file-content-container');

    // Закрытие модалки
    modal.querySelector('.close-modal').addEventListener('click', () => modal.remove());

    try {
        if (file.type === 'application/pdf') {
            // Вариант 1: Используем <embed> (надежный стандартный способ)
            const embed = document.createElement('embed');
            embed.className = 'pdf-embed';
            embed.src = URL.createObjectURL(file);
            embed.type = 'application/pdf';
            container.querySelector('.pdf-viewer-container').appendChild(embed);

            // Вариант 2: PDF.js (для кастомного интерфейса)
            // await renderPdfWithJs(file, container);
        } else {
            // Существующая обработка TXT/DOCX
            const content = file.type === 'text/plain'
                ? await file.text()
                : await readDocxFile(file);
            container.querySelector('pre').textContent = content;
        }
    } catch (error) {
        container.innerHTML = `<p class="error">Ошибка: ${error.message}</p>`;
        console.error(error);
    }
}

// Функция для чтения DOCX файлов
async function readDocxFile(file) {
    try {
        // Используем mammoth.js для чтения DOCX - он проще и надежнее
        const mammoth = await import('https://cdn.jsdelivr.net/npm/mammoth@1.4.0/+esm');
        const arrayBuffer = await file.arrayBuffer();

        const result = await mammoth.extractRawText({ arrayBuffer });
        return result.value; // Возвращаем извлеченный текст
    } catch (error) {
        console.error('Ошибка чтения DOCX:', error);
        return 'Не удалось прочитать содержимое DOCX файла';
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

            if (file.type === 'application/pdf') {
                // PDF открываем в новом окне
                const fileUrl = URL.createObjectURL(file);
                window.open(fileUrl, '_blank');
            } else {
                // TXT и DOCX показываем в модальном окне
                showFileContent(file, file.name);
            }
        });
    });
}
