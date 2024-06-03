""" import os
import cv2
import numpy as np
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.models import save_model
from tensorflow.keras.regularizers import l2
import matplotlib.pyplot as plt

dataset_path = "/content/drive/MyDrive/dataset/"
categories = ["bike", "buses", "car", "truck"]

def preprocess_image(image_path, size=(224, 224)):
    image = cv2.imread(image_path)
    image = cv2.resize(image, size)
    image = np.array(image, dtype=np.float32) / 255.0
    return image

data = []
labels = []

for category in categories:
    folder_path = os.path.join(dataset_path, category)
    for filename in os.listdir(folder_path):
        image_path = os.path.join(folder_path, filename)
        image = preprocess_image(image_path)
        data.append(image)
        labels.append(category)

data = np.array(data)
labels = np.array(labels)
print(f"Processed {len(data)} images.")

label_encoder = LabelEncoder()
labels = label_encoder.fit_transform(labels)
print("Classes:", label_encoder.classes_)

X_train, X_temp, y_train, y_temp = train_test_split(
    data, labels, test_size=0.3, random_state=48
)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.5, random_state=48
)

print(f"Training set size: {len(X_train)}")
print(f"Validation set size: {len(X_val)}")
print(f"Testing set size: {len(X_test)}")

data_augmentation = keras.Sequential(
    [
        layers.RandomFlip("horizontal"),
    ]
)

X_train_aug = []
y_train_aug = []

for image, label in zip(X_train, y_train):
    augmented_image = data_augmentation(tf.expand_dims(image, 0), training=True)
    X_train_aug.append(augmented_image.numpy().squeeze())
    y_train_aug.append(label)

X_train_aug = np.array(X_train_aug)
y_train_aug = np.array(y_train_aug)

print(X_train_aug.shape)
print(y_train_aug.shape)
print(X_val.shape)
print(y_val.shape)
print(X_test.shape)
print(y_test.shape)

model = keras.Sequential(
    [
        layers.Conv2D(32, (3, 3), activation="relu", input_shape=(224, 224, 3), kernel_regularizer=l2(0.02)),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(64, (3, 3), activation="relu", kernel_regularizer=l2(0.02)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Conv2D(128, (3, 3), activation="relu", kernel_regularizer=l2(0.02)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Conv2D(256, (3, 3), activation="relu", kernel_regularizer=l2(0.01)),
        layers.MaxPooling2D((2, 2)),
        layers.Flatten(),
        layers.Dense(512, activation="relu", kernel_regularizer=l2(0.015)),
        layers.Dropout(0.5),
        layers.Dense(4, activation="softmax"),
    ]
)

model.compile(
    optimizer=Adam(),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

model.summary()

history = model.fit(
    X_train_aug,
    y_train_aug,
    epochs=100,
    batch_size=16,
    validation_data=(X_val, y_val),
)

val_loss, val_acc = model.evaluate(X_val, y_val)
print(f"Validation Loss: {val_loss}")
print(f"Validation Accuracy: {val_acc}")

test_loss, test_acc = model.evaluate(X_test, y_test)
print(f"Test Accuracy: {test_acc}")

y_pred = model.predict(X_test)
y_pred_classes = np.argmax(y_pred, axis=1)
print(
    classification_report(
        y_test, y_pred_classes, target_names=["car", "truck", "buses", "bike"]
    )
) """


# # Use the model to predict on new images
# def predict_image(image_path):
#     img = keras.preprocessing.image.load_img(image_path, target_size=img_size)
#     img_array = keras.preprocessing.image.img_to_array(img)
#     img_array = tf.expand_dims(img_array, 0)
#     predictions = model.predict(img_array)
#     return np.argmax(predictions[0])

# # Example usage:
# image_path = 'path/to/new/image.jpg'
# prediction = predict_image(image_path)
# print(f'Predicted class: {prediction}')


import os
import cv2
import numpy as np
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import tensorflow as tf
import keras
from keras import layers
from keras.optimizers import Adam  # type: ignore
from keras.models import save_model  # type: ignore
from keras.regularizers import l2  # type: ignore
import matplotlib.pyplot as plt  # type: ignore

# Dataset paths and categories
dataset_path = "/content/drive/MyDrive/dataset/"
categories = ["bike", "buses", "car", "truck"]


# Function to preprocess the image (improved for clarity)
def preprocess_image(image_path, size=(224, 224)):
    """
    Reads, resizes, and normalizes an image.

    Args:
        image_path (str): Path to the image file.
        size (tuple, optional): Target image size (width, height). Defaults to (224, 224).

    Returns:
        np.ndarray: Preprocessed image as a NumPy array.
    """

    image = cv2.imread(image_path)
    image = cv2.resize(image, size)
    image = np.array(image, dtype=np.float32) / 255.0  # Normalize between 0 and 1
    return image


# Load the data and labels
data = []
labels = []

for category in categories:
    folder_path = os.path.join(dataset_path, category)
    for filename in os.listdir(folder_path):
        image_path = os.path.join(folder_path, filename)
        image = preprocess_image(image_path)
        data.append(image)
        labels.append(category)

data = np.array(data)
labels = np.array(labels)

# Label encoding
label_encoder = LabelEncoder()
labels = label_encoder.fit_transform(labels)
print("Classes:", label_encoder.classes_)

# Data splitting
X_train, X_temp, y_train, y_temp = train_test_split(
    data, labels, test_size=0.3, random_state=48
)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.5, random_state=48
)

print(f"Training set size: {len(X_train)}")
print(f"Validation set size: {len(X_val)}")
print(f"Testing set size: {len(X_test)}")


train_dataset = tf.data.Dataset.from_tensor_slices((X_train, y_train))
val_dataset = tf.data.Dataset.from_tensor_slices((X_val, y_val))
test_dataset = tf.data.Dataset.from_tensor_slices((X_test, y_test))

augmentation = keras.Sequential(
    [
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.2),
        layers.RandomZoom(0.2),
        layers.RandomContrast(0.2),
    ]
)

train_dataset = train_dataset.map(lambda x, y: (augmentation(x, training=True), y))
train_dataset = train_dataset.batch(16).prefetch(buffer_size=tf.data.AUTOTUNE)
val_dataset = val_dataset.batch(16).prefetch(buffer_size=tf.data.AUTOTUNE)
test_dataset = test_dataset.batch(16).prefetch(buffer_size=tf.data.AUTOTUNE)


from keras.applications import VGG16  # type: ignore

base_model = VGG16(weights="imagenet", include_top=False, input_shape=(224, 224, 3))
for layer in base_model.layers:
    layer.trainable = False

# Add a classification head on top of the pre-trained model
x = base_model.output
x = layers.Flatten()(x)
x = layers.Dense(1024, activation="relu")(x)  # Adjust hidden layer size if needed
x = layers.Dropout(0.5)(x)  # Experiment with dropout rate
predictions = layers.Dense(4, activation="softmax")(x)  # 4 for your 4 classes

# Create the final model
model = keras.Model(inputs=base_model.input, outputs=predictions)


model.compile(
    optimizer=Adam(), loss="sparse_categorical_crossentropy", metrics=["accuracy"]
)

model.summary()

history = model.fit(train_dataset, epochs=50, validation_data=val_dataset)


val_loss, val_acc = model.evaluate(X_val, y_val)
print(f"Validation Loss: {val_loss}")
print(f"Validation Accuracy: {val_acc}")

# Evaluate the model on the test set
test_loss, test_acc = model.evaluate(X_test, y_test)
print(f"Test Accuracy: {test_acc}")

# Print the classification report
y_pred = model.predict(X_test)
y_pred_classes = np.argmax(y_pred, axis=1)
print(
    classification_report(
        y_test, y_pred_classes, target_names=["car", "truck", "buses", "bike"]
    )
)


save_model(model, "vehicle_classifier_ZAM5.h5")
print("Model saved successfully!")


""" loss: 1.3189 - accuracy: 0.6681
34/34 [==============================] - 4s 104ms/step - loss: 0.8830 - accuracy: 0.8276 - val_loss: 1.2207 - val_accuracy: 0.6550
Epoch 45/50
34/34 [==============================] - 3s 101ms/step - loss: 0.8480 - accuracy: 0.8435 - val_loss: 1.2349 - val_accuracy: 0.6463
Epoch 46/50
34/34 [==============================] - 3s 101ms/step - loss: 0.8902 - accuracy: 0.8229 - val_loss: 1.2846 - val_accuracy: 0.6419
Epoch 47/50
34/34 [==============================] - 4s 108ms/step - loss: 0.8784 - accuracy: 0.8388 - val_loss: 1.2934 - val_accuracy: 0.6550
Epoch 48/50
34/34 [==============================] - 4s 108ms/step - loss: 0.8475 - accuracy: 0.8388 - val_loss: 1.2162 - val_accuracy: 0.6769
Epoch 49/50
34/34 [==============================] - 4s 105ms/step - loss: 0.8595 - accuracy: 0.8407 - val_loss: 1.2587 - val_accuracy: 0.6507
Epoch 50/50
34/34 [==============================] - 4s 105ms/step - loss: 0.8806 - accuracy: 0.8351 - val_loss: 1.2861 - val_accuracy: 0.6638
model = keras.Sequential(
    [
        layers.Conv2D(
            32,
            (3, 3),
            activation="relu",
            input_shape=(224, 224, 3),
            kernel_regularizer=l2(0.02),
        ),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(64, (3, 3), activation="relu", kernel_regularizer=l2(0.02)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Conv2D(128, (3, 3), activation="relu", kernel_regularizer=l2(0.02)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Conv2D(256, (3, 3), activation="relu", kernel_regularizer=l2(0.01)),
        layers.MaxPooling2D((2, 2)),
        layers.Flatten(),
        layers.Dense(512, activation="relu", kernel_regularizer=l2(0.01)),
        layers.Dropout(0.5),
        layers.Dense(4, activation="softmax"),)]
layers.RandomFlip("horizontal"),

````````````````````````````````````````````````````````````````````````````````````````````````````````````


0s 22ms/step - loss: 2.1452 - accuracy: 0.5808 Test Accuracy: 0.5807860493659973

model = keras.Sequential(
    [
        layers.Conv2D(
            32,
            (3, 3),
            activation="relu",
            input_shape=(224, 224, 3),
            kernel_regularizer=l2(0.02),
        ),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.5),
        layers.Conv2D(64, (3, 3), activation="relu", kernel_regularizer=l2(0.01)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Flatten(),
        layers.Dense(512, activation="relu", kernel_regularizer=l2(0.01)),
        layers.Dropout(0.5),
        layers.Dense(4, activation="softmax"),
    ]
)
 [
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.1),
        layers.RandomZoom(0.2),
    ]

````````````````````````````````````````````````````````````````````````````````````````````````````````````

24ms/step - loss: 1.7282 - accuracy: 0.6114
Test Accuracy: 0.6113536953926086
model = keras.Sequential(
    [
        layers.Conv2D(
            32,
            (3, 3),
            activation="relu",
            input_shape=(224, 224, 3),
            kernel_regularizer=l2(0.02),
        ),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.5),
        layers.Conv2D(64, (3, 3), activation="relu", kernel_regularizer=l2(0.01)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Flatten(),
        layers.Dense(512, activation="relu", kernel_regularizer=l2(0.01)),
        layers.Dropout(0.5),
        layers.Dense(4, activation="softmax"),
    ]
)
layers.RandomFlip("horizontal"),


`````````````````````````````````````````````````````````````````````````````````````````````````````````````




model = keras.Sequential(
    [
        layers.Conv2D(
            32,
            (3, 3),
            activation="relu",
            input_shape=(224, 224, 3),
            kernel_regularizer=l2(0.02),
        ),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Conv2D(64, (3, 3), activation="relu", kernel_regularizer=l2(0.02)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Conv2D(128, (3, 3), activation="relu", kernel_regularizer=l2(0.02)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Conv2D(256, (3, 3), activation="relu", kernel_regularizer=l2(0.02)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Flatten(),
        layers.Dense(512, activation="relu", kernel_regularizer=l2(0.02)),
        layers.Dropout(0.5),
        layers.Dense(4, activation="softmax"),
    ]
)
layers.RandomFlip("horizontal"),


Epoch 47/50
34/34 [==============================] - 3s 96ms/step - loss: 1.1377 - accuracy: 0.6092 - val_loss: 1.1608 - val_accuracy: 0.5895
Epoch 48/50
34/34 [==============================] - 4s 105ms/step - loss: 1.1440 - accuracy: 0.5895 - val_loss: 1.2731 - val_accuracy: 0.5066
Epoch 49/50
34/34 [==============================] - 3s 97ms/step - loss: 1.1321 - accuracy: 0.6017 - val_loss: 1.1965 - val_accuracy: 0.5459
Epoch 50/50
34/34 [==============================] - 3s 100ms/step - loss: 1.1456 - accuracy: 0.5970 - val_loss: 1.2332 - val_accuracy: 0.5415
27ms/step - loss: 1.2818 - accuracy: 0.5109
Test Accuracy: 0.5109170079231262
8/8 [==============================] - 0s 26ms/step
              precision    recall  f1-score   support

           0       0.53      0.77      0.63        57
           1       0.71      0.39      0.50        62
           2       0.39      0.73      0.51        49
           3       0.65      0.21      0.32        61

    accuracy                           0.51       229
   macro avg       0.57      0.53      0.49       229
weighted avg       0.58      0.51      0.49       229





augmenatation one , model shouldnot be complex and less dropouts

``````````````````````````````````````````````````````````````````````````````````````````````````````````````
Epoch 48/50
34/34 [==============================] - 4s 106ms/step - loss: 0.8263 - accuracy: 0.7891 - val_loss: 1.2664 - val_accuracy: 0.6419
Epoch 49/50
34/34 [==============================] - 3s 95ms/step - loss: 0.8356 - accuracy: 0.7985 - val_loss: 1.1698 - val_accuracy: 0.6594
Epoch 50/50
34/34 [==============================] - 4s 105ms/step - loss: 0.7972 - accuracy: 0.8060 - val_loss: 1.2342 - val_accuracy: 0.6681

 24ms/step - loss: 1.3311 - accuracy: 0.6507
Test Accuracy: 0.6506550312042236

model = keras.Sequential(
    [
        layers.Conv2D(
            32,
            (3, 3),
            activation="relu",
            input_shape=(224, 224, 3),
            kernel_regularizer=l2(0.02),
        ),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(64, (3, 3), activation="relu", kernel_regularizer=l2(0.02)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.5),
        layers.Conv2D(128, (3, 3), activation="relu", kernel_regularizer=l2(0.02)),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(256, (3, 3), activation="relu", kernel_regularizer=l2(0.015)),
        layers.MaxPooling2D((2, 2)),
        layers.Flatten(),
        layers.Dense(512, activation="relu", kernel_regularizer=l2(0.01)),
        layers.Dropout(0.5),
        layers.Dense(4, activation="softmax"),
        ])


````````````````````````````````````````````````````````````````````````````````````````````````````
model = keras.Sequential(
    [
        layers.Conv2D(
            32,
            (3, 3),
            activation="relu",
            input_shape=(224, 224, 3),
            kernel_regularizer=l2(0.02),
        ),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(64, (3, 3), activation="relu", kernel_regularizer=l2(0.015)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.5),
        layers.Conv2D(128, (3, 3), activation="relu", kernel_regularizer=l2(0.015)),
        layers.MaxPooling2D((2, 2)),
        layers.Flatten(),
        layers.Dense(512, activation="relu", kernel_regularizer=l2(0.01)),
        layers.Dropout(0.5),
        layers.Dense(4, activation="softmax"),
        ])
loss: 1.3680 - accuracy: 0.6594
Test Accuracy: 0.6593886613845825
34/34 [==============================] - 4s 104ms/step - loss: 1.0272 - accuracy: 0.7545 - val_loss: 1.1694 - val_accuracy: 0.7336
 loss: 0.8482 - accuracy: 0.8519
 """
