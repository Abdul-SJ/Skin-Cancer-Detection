import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Set image size and paths
IMG_SIZE = 224
BATCH_SIZE = 32

train_dir = r"C:\Users\Mian Usman\Desktop\SkinCancerWebApp\melanoma_cancer_dataset\train"
test_dir = r"C:\Users\Mian Usman\Desktop\SkinCancerWebApp\melanoma_cancer_dataset\test"

# Image augmentation and normalization
train_gen = ImageDataGenerator(rescale=1./255, rotation_range=15, zoom_range=0.2, shear_range=0.2, horizontal_flip=True)
test_gen = ImageDataGenerator(rescale=1./255)

train_data = train_gen.flow_from_directory(train_dir, target_size=(IMG_SIZE, IMG_SIZE), batch_size=BATCH_SIZE, class_mode='binary')
test_data = test_gen.flow_from_directory(test_dir, target_size=(IMG_SIZE, IMG_SIZE), batch_size=BATCH_SIZE, class_mode='binary')

# Build CNN model
model = Sequential([
    Conv2D(32, (3,3), activation='relu', input_shape=(IMG_SIZE, IMG_SIZE, 3)),
    MaxPooling2D(2,2),
    
    Conv2D(64, (3,3), activation='relu'),
    MaxPooling2D(2,2),
    
    Conv2D(128, (3,3), activation='relu'),
    MaxPooling2D(2,2),

    Flatten(),
    Dense(128, activation='relu'),
    Dropout(0.5),
    Dense(1, activation='sigmoid')  # Binary classification: benign (0) or malignant (1)
])

# Compile model
model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# Train the model
history = model.fit(
    train_data,
    validation_data=test_data,
    epochs=10
)

# Save the model locally
model.save("Skin_Cancer_CNN_Local.h5")
print("Model saved as Skin_Cancer_CNN_Local.h5")
