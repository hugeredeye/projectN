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

document.getElementById('tz-input').addEventListener('change', function(e) {
    handleFileUpload('tz', e.target.files[0]);
});

document.getElementById('doc-input').addEventListener('change', function(e) {
    handleFileUpload('doc', e.target.files[0]);
});

function handleFileUpload(type, file) {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            uploadedFiles[type] = file;
            updateFileList(type, file);
        }
    })
    .catch(error => {
        console.error('Ошибка загрузки:', error);
        alert('Ошибка при загрузке файла');
    });
}

function updateFileList(type, file) {
    const fileList = document.getElementById('file-list');
    
    // Удаляем предыдущий файл того же типа
    const existingFiles = fileList.querySelectorAll(`[data-type="${type}"]`);
    existingFiles.forEach(el => el.remove());
    
    // Добавляем новый файл
    const fileItem = document.createElement('div');
    fileItem.textContent = file.name;
    fileItem.setAttribute('data-type', type);
    fileList.appendChild(fileItem);
}

function compareDocuments() {
    if (!uploadedFiles.tz || !uploadedFiles.doc) {
        alert('Пожалуйста, загрузите оба файла');
        return;
    }

    const formData = new FormData();
    formData.append('tz_file', uploadedFiles.tz);
    formData.append('project_file', uploadedFiles.doc);

    fetch('/compare', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Результат сравнения:', data);
        if (data.status === 'success') {
            alert('Файлы успешно загружены и готовы к сравнению');
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Произошла ошибка при сравнении документов');
    });
}
