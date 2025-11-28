from src.models.db import db
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import pyotp
import qrcode
import io
import base64

ph = PasswordHasher()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Campos para MFA
    mfa_enabled = db.Column(db.Boolean, default=False, nullable=False)
    mfa_secret = db.Column(db.String(32), nullable=True)
    is_sensitive_account = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """Hash and set the user's password using Argon2"""
        self.password_hash = ph.hash(password)

    def verify_password(self, password):
        """Verify a password against the stored hash"""
        try:
            ph.verify(self.password_hash, password)
            # Check if rehashing is needed (if parameters have changed)
            if ph.check_needs_rehash(self.password_hash):
                self.password_hash = ph.hash(password)
                db.session.commit()
            return True
        except VerifyMismatchError:
            return False

    def generate_mfa_secret(self):
        """Generate a new TOTP secret for MFA"""
        self.mfa_secret = pyotp.random_base32()
        return self.mfa_secret

    def get_totp_uri(self):
        """Get the provisioning URI for TOTP (for QR code generation)"""
        if not self.mfa_secret:
            return None
        return pyotp.totp.TOTP(self.mfa_secret).provisioning_uri(
            name=self.email,
            issuer_name='EventoApp'
        )

    def generate_qr_code(self):
        """Generate QR code for TOTP setup"""
        uri = self.get_totp_uri()
        if not uri:
            return None
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Return base64 encoded image
        return base64.b64encode(buffer.getvalue()).decode()

    def verify_totp(self, token):
        """Verify a TOTP token"""
        if not self.mfa_secret:
            return False
        
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token, valid_window=1)

    def enable_mfa(self):
        """Enable MFA for this user"""
        if not self.mfa_secret:
            self.generate_mfa_secret()
        self.mfa_enabled = True

    def disable_mfa(self):
        """Disable MFA for this user"""
        self.mfa_enabled = False
        self.mfa_secret = None

    def requires_mfa(self):
        """Check if user requires MFA"""
        return self.is_sensitive_account and self.mfa_enabled

    def to_dict(self, include_mfa_status=False):
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email
        }
        if include_mfa_status:
            data['mfa_enabled'] = self.mfa_enabled
            data['is_sensitive_account'] = self.is_sensitive_account
        return data
