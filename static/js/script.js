document.getElementById('compareForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    const tzFile = document.getElementById('tzFile').files[0];
    const projectFile = document.getElementById('projectFile').files[0];

    const formData = new FormData();
    formData.append('tz_file', tzFile);
    formData.append('project_file', projectFile);

    const response = await fetch('/compare', {
        method: 'POST',
        body: formData
    });

    const result = await response.json();
    document.getElementById('compareResult').innerText = JSON.stringify(result, null, 2);
});

document.getElementById('explainForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    const point = document.getElementById('point').value;

    const response = await fetch('/explain', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ point: point })
    });

    const result = await response.json();
    document.getElementById('explainResult').innerText = JSON.stringify(result, null, 2);
});

// Глобальные переменные для хранения файлов
let tzFile = null;
let docFile = null;

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация обработчиков для загрузки файлов
    const tzInput = document.getElementById('tz-input');
    const docInput = document.getElementById('doc-input');
    const compareButton = document.getElementById('compare-button');
    const uploadedFiles = document.getElementById('uploaded-files');
    const fileList = document.getElementById('file-list');

    // Обработчики изменения файлов
    tzInput.addEventListener('change', (e) => handleFileSelect(e, 'tz'));
    docInput.addEventListener('change', (e) => handleFileSelect(e, 'doc'));

    // Обработчик кнопки сравнения
    compareButton.addEventListener('click', handleCompare);

    // Функция обработки выбора файла
    function handleFileSelect(event, type) {
        const file = event.target.files[0];
        if (file) {
            if (type === 'tz') {
                tzFile = file;
            } else {
                docFile = file;
            }
            updateFileList();
        }
    }

    // Функция обновления списка файлов
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

    // Функция отправки файлов на сервер
    async function handleCompare() {
        if (!tzFile || !docFile) {
            alert('Пожалуйста, загрузите оба файла');
            return;
        }

        compareButton.disabled = true;
        
        try {
            const formData = new FormData();
            formData.append('tz_file', tzFile);
            formData.append('project_file', docFile);

            const response = await fetch('/compare', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.status === 'processing') {
                // Сохраняем session_id в localStorage для использования на странице обработки
                localStorage.setItem('processing_session_id', data.session_id);
                window.location.href = '/processing';
            } else {
                throw new Error(data.message || 'Произошла ошибка при загрузке файлов');
            }
        } catch (error) {
            alert(error.message);
            compareButton.disabled = false;
        }
    }
});
