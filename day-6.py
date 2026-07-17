# M2 Day 6 - Linear Regression (Feynman own build: predict study minutes -> score)

from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

# Own toy data: hours studied vs test score
X = [[1], [2], [3], [4], [5], [6], [7], [8]]
y = [50, 55, 61, 68, 72, 78, 85, 90]

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=1)
model = LinearRegression()
model.fit(X_tr, y_tr)
pred = model.predict(X_te)
print("R2:", round(r2_score(y_te, pred), 3))
print("predict 10h ->", round(model.predict([[10]])[0], 1))

# RL link: regression = function approximation, same idea as value-function in RL
print("slope:", round(model.coef_[0], 2), "intercept:", round(model.intercept_, 2))
