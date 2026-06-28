def recalibrate_omega(predictions: list[dict], actuals: list[dict], current_omega: dict) -> dict:
    """Recalibrate adaptive omega (ω) coefficients using Gradient Descent.

    predictions: list of dict with 'w1', 'w2', 'w3', 'predicted'
    actuals: list of dict with 'actual'
    """
    if len(predictions) != len(actuals) or not predictions:
        return current_omega

    w1 = current_omega.get("w1", 0.35)
    w2 = current_omega.get("w2", 0.40)
    w3 = current_omega.get("w3", 0.25)

    lr = 0.01
    grad_w1, grad_w2, grad_w3 = 0.0, 0.0, 0.0

    for pred, act in zip(predictions, actuals):
        error = pred["predicted"] - act["actual"]
        # Contribution gradient proxy based on previous weights
        grad_w1 += error * pred.get("w1", w1)
        grad_w2 += error * pred.get("w2", w2)
        grad_w3 += error * pred.get("w3", w3)

    n = len(predictions)
    w1 -= lr * (grad_w1 / n)
    w2 -= lr * (grad_w2 / n)
    w3 -= lr * (grad_w3 / n)

    # Apply constraint w >= 0.1
    w1 = max(0.1, w1)
    w2 = max(0.1, w2)
    w3 = max(0.1, w3)

    # Apply constraint sum(w) = 1.0
    total = w1 + w2 + w3
    w1 = round(w1 / total, 4)
    w2 = round(w2 / total, 4)
    w3 = round(w3 / total, 4)

    # Final normalization adjustment
    diff = 1.0 - (w1 + w2 + w3)
    w2 = round(w2 + diff, 4)

    return {"w1": w1, "w2": w2, "w3": w3}
