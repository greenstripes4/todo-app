from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from app import db

user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET', 'PUT'])
@jwt_required()
def users():
    current_user_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_user_username).first()

    if current_user.role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403

    if request.method == 'GET':
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)

        paginated_users = User.query.paginate(page=page, per_page=per_page)

        users_list = [user.to_dict() for user in paginated_users.items]

        pagination_metadata = {
            'total_pages': paginated_users.pages,
            'current_page': paginated_users.page,
            'per_page': paginated_users.per_page,
            'total_users': paginated_users.total
        }

        return jsonify({'users': users_list, 'pagination': pagination_metadata}), 200

    elif request.method == 'PUT':
        data = request.get_json()
        user_id = data.get('id')
        new_role = data.get('role')
        new_status = data.get('status')

        if not user_id or not new_role or not new_status:
            return jsonify({'message': 'User ID, new role, and new status are required'}), 400

        user = User.query.get(user_id)

        if not user:
            return jsonify({'message': 'User not found'}), 404

        user.role = new_role
        user.status = new_status
        db.session.commit()

        return jsonify({'message': 'User updated successfully'}), 200
