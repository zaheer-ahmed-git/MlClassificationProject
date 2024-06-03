from transformers import BertTokenizer, BertForSequenceClassification
from transformers import Trainer, TrainingArguments

# Sample data
documents = [
    "I love this movie, it's amazing!",
    "This film was a waste of time.",
    "Absolutely fantastic, I enjoyed it.",
    "Not my cup of tea, very boring."
]
labels = [1, 0, 1, 0]  # 1 for positive sentiment, 0 for negative sentiment

# Tokenization
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
tokens = tokenizer(documents, padding=True, truncation=True, return_tensors='pt')

# Model initialization
model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2)

# Training arguments
training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=3,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    warmup_steps=500,
    weight_decay=0.01,
    logging_dir='./logs',
)

# Trainer initialization
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=(tokens, labels),
    eval_dataset=(tokens, labels)
)

# Model training
trainer.train()
