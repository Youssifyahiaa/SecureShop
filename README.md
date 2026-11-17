# SecureShop

Team: Youssef, Sandy, Ali, Mark.

## Setup (Windows)

```
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Open `.env` and replace `SECRET_KEY` with a random value:

```
py -c "import secrets; print(secrets.token_hex(32))"
```

## Run (development only)

```
flask --app app run --debug
```

Open http://127.0.0.1:5000

## Tests

```
python -m pytest -q
```

## Where your code goes

| Folder | Owner |
|---|---|
| app/auth, app/checkout | Youssef |
| app/catalog, app/cart | Mark |
| app/promotions | Ali |
| app/account, app/admin | Sandy |

Each folder already has a blueprint called `bp`. Add your routes inside your own folder only;
`create_app()` registers it automatically. Shared objects:

```python
from app import create_app            # create_app(test_config=None)
from app.extensions import db, login_manager, csrf, limiter, migrate
```

Work on your own branch (`git checkout -b feature/<name>`) and open a pull request into `main`.
