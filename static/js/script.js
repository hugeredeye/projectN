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

function updateFileList() {
    let fileNames = [];
    if (tzFile) fileNames.push(tzFile.name);
    if (docFile) fileNames.push(docFile.name);

    if (fileNames.length > 0) {
        fileList.innerHTML = fileNames.join('<br>');
        uploadedFiles.style.display = 'block';
        compareButton.style.display = fileNames.length === 2 ? 'flex' : 'none';
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