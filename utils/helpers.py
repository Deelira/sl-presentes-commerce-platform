import re
import secrets
import unicodedata
from werkzeug.utils import secure_filename


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or secrets.token_hex(4)


def generate_order_code():
    return "PED-" + secrets.token_hex(4).upper()


def save_upload(file_storage, upload_folder):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in {"png", "jpg", "jpeg", "webp", "gif"}:
        return None
    filename = secure_filename(f"{secrets.token_hex(8)}.{ext}")
    path = upload_folder / filename
    file_storage.save(path)
    return f"/static/images/uploads/{filename}"
