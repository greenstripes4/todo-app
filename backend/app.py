import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS

# Initialize the Flask application
app = Flask(__name__)

# Configure CORS to accept all domains
CORS(app)

# Fetch database URI from environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

# Fetch JWT secret key from environment variable
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')

# Initialize the SQLAlchemy database extension
db = SQLAlchemy(app)
# Initialize the JWTManager extension
jwt = JWTManager(app)

# Import the User model from the models package
from models.user import User
# Import the WebsiteAccount model
from models.website_account import WebsiteAccount

# Create tables in the database if they don't exist
with app.app_context():
    db.create_all()

    # --- Admin User Creation ---
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        # Create the admin user
        admin_user = User(username='admin', role='admin', status='active')
        admin_user.set_password('admin')
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created.")
        # Re-query admin_user to get the ID after commit
        admin_user = User.query.filter_by(username='admin').first()
    else:
        print("Admin user already exists.")

    # --- Sample Website Account Creation for Admin ---
    # Check if the admin user exists and doesn't already have this specific sample account
    if admin_user:
        sample_account_url = 'https://admin-sample-site.com'
        existing_sample_account = WebsiteAccount.query.filter_by(
            user_id=admin_user.id,
            website_url=sample_account_url
        ).first()

        if not existing_sample_account:
            sample_account = WebsiteAccount(
                user_id=admin_user.id,
                website_url=sample_account_url,
                account_name='Admin Sample Account',
                account_email='admin@sample-site.com',
                compliance_contact='compliance@sample-site.com'
            )
            db.session.add(sample_account)
            db.session.commit()
            print(f"Sample website account created for admin user.")
        else:
            print(f"Sample website account for admin user already exists.")
    else:
        # This case should ideally not happen based on the logic above, but good for safety
        print("Admin user not found, cannot create sample website account.")
    # --- End Sample Website Account Creation ---


# Import routes from the routes package
from routes.auth import auth_bp
from routes.user import user_bp
from routes.website_account import website_account_bp
from routes.health import health_bp

# Register the blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(website_account_bp)
app.register_blueprint(health_bp)

# Define the root route (just a simple hello message)
@app.route('/')
def hello():
    return jsonify({'message': 'Hello from Flask!'})

# Run the app if the script is executed directly
if __name__ == '__main__':
    # Make sure debug is False in production!
    # Use environment variable for debug flag if possible
    is_debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=is_debug, host='0.0.0.0')
