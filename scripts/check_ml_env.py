"""Kiem tra cac thu vien hoc may co import duoc tren may hien tai khong."""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODULES = ["numpy", "pandas", "statsmodels", "xgboost", "prophet", "cmdstanpy"]

print("=" * 60)
print("KIEM TRA THU VIEN HOC MAY")
print("=" * 60)
print(f"Python: {sys.version.split()[0]}")
print("-" * 60)

for name in MODULES:
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", "?")
        print(f"{name:14} OK       version={version}")
    except Exception as exc:  # noqa: BLE001
        print(f"{name:14} FAIL     {type(exc).__name__}: {exc}")

print("-" * 60)

# Prophet can import fine but still fail at runtime because it needs the
# CmdStan binary compiled/linked. Test that separately.
try:
    from prophet import Prophet

    print("Dang khoi tao Prophet (can CmdStan)...")
    model = Prophet()
    print("Prophet: khoi tao THANH CONG")
except Exception as exc:  # noqa: BLE001
    print(f"Prophet: LOI khoi tao -> {type(exc).__name__}: {exc}")

try:
    import cmdstanpy

    print(f"CmdStan path: {cmdstanpy.cmdstan_path()}")
except Exception as exc:  # noqa: BLE001
    print(f"CmdStan: chua cai -> {type(exc).__name__}: {exc}")

try:
    from xgboost import XGBRegressor

    model = XGBRegressor(n_estimators=5, max_depth=3)
    model.fit([[1], [2], [3], [4]], [10, 20, 30, 40])
    pred = model.predict([[5]])
    print(f"XGBoost: train+predict OK, pred={pred[0]:.2f}")
except Exception as exc:  # noqa: BLE001
    print(f"XGBoost: LOI -> {type(exc).__name__}: {exc}")

try:
    from statsmodels.tsa.arima.model import ARIMA

    model = ARIMA([10, 12, 11, 13, 12], order=(1, 0, 0))
    model.fit()
    print("ARIMA (statsmodels): train OK")
except Exception as exc:  # noqa: BLE001
    print(f"ARIMA: LOI -> {type(exc).__name__}: {exc}")

print("=" * 60)
