# M2 Day 5 - First ML model: iris classification (Feynman own build)

from sklearn.datasets import load_iris
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Load data (own: not copied notebook)
X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

model = DecisionTreeClassifier(max_depth=3)
model.fit(X_train, y_train)
pred = model.predict(X_test)
print("accuracy:", accuracy_score(y_test, pred))

# RL link: model learns pattern from labeled data (supervised) = agent learning from examples
print("features per sample:", X.shape[1], "| classes:", len(set(y)))
