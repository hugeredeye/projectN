import os
import torch
from transformers import Trainer, TrainingArguments, AutoModelForSequenceClassification, AutoTokenizer
from sklearn.metrics import accuracy_score

# Загрузка модели и токенизатора
model_name = "bert-base-uncased"  # Вы можете выбрать другую модель
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

# Подготовка данных
def load_data():
    # Замените этот код на загрузку ваших данных
    train_texts = ["Текст 1", "Текст 2"]  # Примеры текстов
    train_labels = [0, 1]  # Примеры меток (0 - несоответствие, 1 - соответствие)
    return train_texts, train_labels

train_texts, train_labels = load_data()

# Токенизация данных
train_encodings = tokenizer(train_texts, truncation=True, padding=True)

# Создание Dataset
class CustomDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

train_dataset = CustomDataset(train_encodings, train_labels)

# Настройка аргументов обучения
training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=3,
    per_device_train_batch_size=8,
    save_steps=10_000,
    save_total_limit=2,
)

# Создание Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
)

# Обучение модели
trainer.train()

# Сохранение модели
model.save_pretrained("./trained_model")
tokenizer.save_pretrained("./trained_model")