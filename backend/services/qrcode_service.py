import qrcode
from io import BytesIO
import base64

def generate_qr_code(app_links):
    qr = qrcode.make("\n".join(app_links))
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()
