# /config/workspace/todo-app/backend/models/user.py
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    # Primary key (auto-incrementing integer)
    id = db.Column(db.Integer, primary_key=True)
    # Username (unique, non-nullable string)
    username = db.Column(db.String(80), unique=True, nullable=False)
    # Password hash (non-nullable string)
    password_hash = db.Column(db.String(256), nullable=False)
    # User role (admin, normal, deactivated)
    role = db.Column(db.String(20), default='normal')
    # User status (active, deactivated)
    status = db.Column(db.String(20), default='active')  # Added status field

    # Method to set the user's password (hashes the password)
    def set_password(self, password):
        # Generate a password hash using werkzeug.security
        self.password_hash = generate_password_hash(password)

    # Method to check if a given password matches the stored hash
    def check_password(self, password):
        # Check the password against the stored hash using werkzeug.security
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'status': self.status
        }
