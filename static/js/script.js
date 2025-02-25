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

let uploadedFiles = {
    tz: null,
    doc: null
};

// Добавляем отладочные сообщения
document.getElementById('tz-input').addEventListener('change', function(e) {
    console.log('Выбран файл ТЗ:', e.target.files[0]?.name);
    handleFileUpload('tz', e.target.files[0]);
});

document.getElementById('doc-input').addEventListener('change', function(e) {
    console.log('Выбран файл документации:', e.target.files[0]?.name);
    handleFileUpload('doc', e.target.files[0]);
});

function handleFileUpload(type, file) {
    if (!file) {
        console.log('Файл не выбран');
        return;
    }

    console.log(`Начинаем загрузку файла ${file.name}`);
    const formData = new FormData();
    formData.append('file', file);

    // Отправляем файл на сервер
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Получен ответ от сервера:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('Данные от сервера:', data);
        if (data.status === 'success') {
            uploadedFiles[type] = file;
            updateFileList();
            checkShowCompareButton();
        }
    })
    .catch(error => {
        console.error('Ошибка загрузки:', error);
        alert('Ошибка при загрузке файла: ' + error.message);
    });
}

function updateFileList() {
    console.log('Обновляем список файлов');
    const fileList = document.getElementById('file-list');
    const uploadedFilesDiv = document.getElementById('uploaded-files');
    
    let hasFiles = false;
    let fileListHTML = '';

    if (uploadedFiles.tz) {
        fileListHTML += `${uploadedFiles.tz.name}<br>`;
        hasFiles = true;
        console.log('Добавлен файл ТЗ в список');
    }
    if (uploadedFiles.doc) {
        fileListHTML += uploadedFiles.doc.name;
        hasFiles = true;
        console.log('Добавлен файл документации в список');
    }

    fileList.innerHTML = fileListHTML;
    uploadedFilesDiv.style.display = hasFiles ? 'block' : 'none';
    console.log('Отображение списка файлов:', hasFiles ? 'показан' : 'скрыт');
}

function checkShowCompareButton() {
    console.log('Проверяем необходимость показа кнопки сравнения');
    const compareButton = document.getElementById('compare-button');
    const shouldShow = uploadedFiles.tz || uploadedFiles.doc;
    compareButton.style.display = shouldShow ? 'block' : 'none';
    console.log('Кнопка сравнения:', shouldShow ? 'показана' : 'скрыта');
}

document.getElementById('compare-button').addEventListener('click', function() {
    console.log('Нажата кнопка сравнения');
    const formData = new FormData();
    
    if (uploadedFiles.tz) {
        formData.append('tz_file', uploadedFiles.tz);
        console.log('Добавлен ТЗ в запрос');
    }
    if (uploadedFiles.doc) {
        formData.append('project_file', uploadedFiles.doc);
        console.log('Добавлена документация в запрос');
    }

    fetch('/compare', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Получен результат сравнения:', data);
        if (data.status === 'success') {
            alert('Файлы успешно сравнены!');
        }
    })
    .catch(error => {
        console.error('Ошибка сравнения:', error);
        alert('Произошла ошибка при сравнении документов');
    });
});
