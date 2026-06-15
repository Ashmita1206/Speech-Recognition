import os
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from tensorflow.keras.utils import to_categorical
from utils.dataset import load_dataset
from model.model import build_model

def plot_history(history, save_path="training_history.png"):
    plt.figure(figsize=(12, 4))

    # Plot loss
    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Train Loss')
    plt.plot(history.history['val_loss'], label='Val Loss')
    plt.title('Model Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()

    # Plot accuracy
    plt.subplot(1, 2, 2)
    plt.plot(history.history['accuracy'], label='Train Accuracy')
    plt.plot(history.history['val_accuracy'], label='Val Accuracy')
    plt.title('Model Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()

    plt.tight_layout()
    plt.savefig(save_path)
    print(f"Training history plot saved to {save_path}")

def main():
    print("Loading dataset...")
    X, y, label_map = load_dataset("data")
    
    if len(X) == 0:
        print("Error: No data loaded. Please check the data directory.")
        return

    num_classes = len(label_map)
    print(f"Dataset shape: {X.shape}")
    print(f"Classes: {label_map}")

    # One-hot encode labels
    y_categorical = to_categorical(y, num_classes=num_classes)

    # Train-test split (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(X, y_categorical, test_size=0.2, random_state=42)
    print(f"Train set: {X_train.shape}, Test set: {X_test.shape}")

    # Build model
    model = build_model((X.shape[1], X.shape[2]), num_classes=num_classes)
    model.summary()

    # Train
    print("Starting training...")
    history = model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=20, batch_size=8)

    # Save model
    model_save_path = os.path.join("model", "speech_model.keras")
    model.save(model_save_path)
    print(f"Model saved to {model_save_path}")

    # Save label map
    label_map_path = os.path.join("model", "label_map.json")
    with open(label_map_path, 'w') as f:
        json.dump(label_map, f)
    print(f"Label map saved to {label_map_path}")

    # Plot history
    plot_history(history)

if __name__ == "__main__":
    main()