# /config/workspace/todo-app/backend/models/website_account.py
from app import db
from sqlalchemy.orm import relationship

class WebsiteAccount(db.Model):
    __tablename__ = 'website_accounts' # Optional: Define a specific table name

    # Primary key (auto-incrementing integer)
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key linking to the User table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # URL of the website
    website_url = db.Column(db.String(2048), nullable=False) # Using 2048 for URL length flexibility
    # Account name/username on the website
    account_name = db.Column(db.String(255), nullable=True) # Nullable if email is the primary identifier or name isn't used
    # Email address associated with the account
    account_email = db.Column(db.String(255), nullable=False)
    # Contact info (URL or email) for compliance requests (e.g., DSAR, deletion)
    compliance_contact = db.Column(db.String(2048), nullable=True) # Nullable as it might not always be known

    # Define the relationship back to the User model
    # 'backref' creates a virtual 'website_accounts' attribute on the User model
    # 'lazy=True' means related accounts are loaded only when accessed
    user = relationship('User', backref=db.backref('website_accounts', lazy=True))

    def __repr__(self):
        # Helpful representation for debugging
        return f'<WebsiteAccount {self.website_url} for User {self.user_id}>'

    def to_dict(self):
        # Method to serialize the object data to a dictionary
        return {
            'id': self.id,
            'user_id': self.user_id,
            'website_url': self.website_url,
            'account_name': self.account_name,
            'account_email': self.account_email,
            'compliance_contact': self.compliance_contact
        }
