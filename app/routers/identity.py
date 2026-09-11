import hashlib
import uuid

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.storage import read_json, write_json

router = APIRouter(tags=["identity"])

CUSTOMERS_FILE = "customers.json"


class RegisterRequest(BaseModel):
    name: str
    secret: str
    role: str  # "shopper" | "owner"


class LoginRequest(BaseModel):
    name: str
    secret: str


def _key(name: str) -> str:
    """Normalize a name for lookup: 'Priya  M ' -> 'priya-m'"""
    return " ".join(name.strip().split()).lower().replace(" ", "-")


def _hash_secret(secret: str) -> str:
    """Secrets are stored hashed, never in plain text."""
    return hashlib.sha256(secret.strip().lower().encode()).hexdigest()


def _display(name: str) -> str:
    return " ".join(name.strip().split())


def _suggestions(name: str, customers: dict):
    """Gmail-style: if 'Priya' is taken, offer 'Priya-M', 'Priya-S', 'Priya 2'..."""
    base = _display(name)
    out = []
    for suffix, joiner in [("-M", ""), ("-S", ""), ("-K", ""), ("2", " "), ("7", " ")]:
        candidate = base + (joiner + suffix if joiner else suffix)
        if _key(candidate) not in customers:
            out.append(candidate)
        if len(out) == 3:
            break
    return out


@router.post("/identity/register", status_code=201)
def register(body: RegisterRequest):
    name = _display(body.name)
    if len(name) < 2:
        return JSONResponse(status_code=400, content={"message": "That name is a little short - try 2+ characters."})
    if len(body.secret.strip()) < 3:
        return JSONResponse(status_code=400, content={"message": "Secret word needs at least 3 characters."})

    role = body.role if body.role in ("shopper", "owner") else "shopper"

    customers = read_json(CUSTOMERS_FILE, {})
    if _key(name) in customers:
        return JSONResponse(
            status_code=409,
            content={"message": "name taken", "suggestions": _suggestions(name, customers)},
        )

    customer_id = "cust-" + uuid.uuid4().hex[:10]
    customers[_key(name)] = {
        "id": customer_id,
        "name": name,
        "secret_hash": _hash_secret(body.secret),
        "role": role,
    }
    write_json(CUSTOMERS_FILE, customers)
    return {"customer_id": customer_id, "name": name, "role": role}


@router.post("/identity/login")
def login(body: LoginRequest):
    customers = read_json(CUSTOMERS_FILE, {})
    record = customers.get(_key(body.name))
    if not record:
        return JSONResponse(status_code=404, content={"message": "No profile with that name yet."})
    if record["secret_hash"] != _hash_secret(body.secret):
        # 403 (not 401) on purpose: 401 is reserved for the API key on this app
        return JSONResponse(status_code=403, content={"message": "That secret word doesn't match."})
    return {"customer_id": record["id"], "name": record["name"], "role": record["role"]}