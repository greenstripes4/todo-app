from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import os

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

# Define the User model (database table)
class User(db.Model):
    # Primary key (auto-incrementing integer)
    id = db.Column(db.Integer, primary_key=True)
    # Username (unique, non-nullable string)
    username = db.Column(db.String(80), unique=True, nullable=False)
    # Password hash (non-nullable string)
    password_hash = db.Column(db.String(256), nullable=False)
    # User role (admin, normal, deactivated)
    role = db.Column(db.String(20), default='normal')  # Added role field

    # Method to set the user's password (hashes the password)
    def set_password(self, password):
        # Generate a password hash using werkzeug.security
        self.password_hash = generate_password_hash(password)

    # Method to check if a given password matches the stored hash
    def check_password(self, password):
        # Check the password against the stored hash using werkzeug.security
        return check_password_hash(self.password_hash, password)

# Create tables in the database if they don't exist
with app.app_context():
    db.create_all()

    # Check if the admin user already exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        # Create the admin user
        admin_user = User(username='admin', role='admin')  # Set role to admin
        admin_user.set_password('admin')
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin user already exists.")

# Define the root route (just a simple hello message)
@app.route('/')
def hello():
    return jsonify({'message': 'Hello from Flask!'})

# Define the /register route (handles user registration)
@app.route('/register', methods=['POST'])
def register():
    # Get the JSON data from the request body
    data = request.get_json()
    # Extract the username and password from the JSON data
    username = data.get('username')
    password = data.get('password')

    # Validate that both username and password are provided
    if not username or not password:
        # Return a 400 (Bad Request) error if either is missing
        return jsonify({'message': 'Username and password are required'}), 400

    # Check if a user with the given username already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        # Return a 409 (Conflict) error if the username is already taken
        return jsonify({'message': 'Username already exists'}), 409

    # Create a new User object
    new_user = User(username=username)
    # Set the user's password (hashes it automatically)
    new_user.set_password(password)
    # Add the new user to the database session
    db.session.add(new_user)
    # Commit the changes to the database
    db.session.commit()

    # Return a 201 (Created) success message
    return jsonify({'message': 'User registered successfully'}), 201

# Define the /login route (handles user login)
@app.route('/login', methods=['POST'])
def login():
    # Get the JSON data from the request body
    data = request.get_json()
    # Extract the username and password from the JSON data
    username = data.get('username')
    password = data.get('password')

    # Validate that both username and password are provided
    if not username or not password:
        # Return a 400 (Bad Request) error if either is missing
        return jsonify({'message': 'Username and password are required'}), 400

    # Find the user with the given username
    user = User.query.filter_by(username=username).first()

    # Check if the user exists and the password is correct
    if user and user.check_password(password):
        # Create an access token for the user, including the role
        additional_claims = {"role": user.role}
        access_token = create_access_token(identity=username, additional_claims=additional_claims)
        # Return the access token, the role and a success message
        return jsonify({'message': 'Logged in successfully', 'access_token': access_token, 'role': user.role}), 200
    else:
        # Return a 401 (Unauthorized) error if the login is incorrect
        return jsonify({'message': 'Invalid username or password'}), 401

# Define the /update-password route (handles user password update)
@app.route('/update-password', methods=['POST'])
@jwt_required()  # Protect this route with JWT authentication
def update_password():
    # Get the JSON data from the request body
    data = request.get_json()
    # Extract the old password and new password from the JSON data
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    # Validate that both old_password and new_password are provided
    if not old_password or not new_password:
        # Return a 400 (Bad Request) error if either is missing
        return jsonify({'message': 'Old password and new password are required'}), 400

    # Get the identity of the current user from the JWT token
    current_user_username = get_jwt_identity()
    # Find the user with the given username
    user = User.query.filter_by(username=current_user_username).first()

    # Check if the user exists and the old password is correct
    if user and user.check_password(old_password):
        # Set the new password (hashes it automatically)
        user.set_password(new_password)
        # Commit the changes to the database
        db.session.commit()
        # Return a success message
        return jsonify({'message': 'Password updated successfully'}), 200
    else:
        # Return a 401 (Unauthorized) error if the old password is incorrect
        return jsonify({'message': 'Invalid old password'}), 401

# Run the app if the script is executed directly
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
