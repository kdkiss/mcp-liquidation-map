import hmac

from flask import Blueprint, jsonify, request, current_app
from marshmallow import Schema, ValidationError, fields
from sqlalchemy.exc import IntegrityError

from mcp_liquidation_map.models.user import User, db


user_bp = Blueprint('user', __name__)


class UserSchema(Schema):
    username = fields.Str(required=True)
    email = fields.Email(required=True)


user_schema = UserSchema()


@user_bp.before_request
def require_user_api_token():
    token = current_app.config.get("USER_API_TOKEN")
    if not token:
        return (
            jsonify({"error": "User API token is not configured."}),
            503,
        )

    auth_header = request.headers.get("Authorization", "")
    scheme, _, supplied_token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not supplied_token:
        return (
            jsonify({"error": "Missing or invalid authorization token."}),
            401,
        )

    if not hmac.compare_digest(supplied_token, token):
        return jsonify({"error": "Invalid authorization token."}), 401


@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])


@user_bp.route('/users', methods=['POST'])
def create_user():
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({'errors': {'_schema': ['Invalid or missing JSON payload.']}}), 400

    try:
        data = user_schema.load(payload)
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400

    user = User(username=data['username'], email=data['email'])
    db.session.add(user)

    try:
        db.session.commit()
    except IntegrityError as err:
        db.session.rollback()
        return _handle_integrity_error(err)

    return jsonify(user.to_dict()), 201


@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({'errors': {'_schema': ['Invalid or missing JSON payload.']}}), 400

    try:
        data = user_schema.load(payload, partial=True)
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400

    if not data:
        return jsonify({'errors': {'_schema': ['No valid fields were provided for update.']}}), 400

    for key, value in data.items():
        setattr(user, key, value)

    try:
        db.session.commit()
    except IntegrityError as err:
        db.session.rollback()
        return _handle_integrity_error(err)

    return jsonify(user.to_dict())


@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return '', 204


def _handle_integrity_error(error: IntegrityError):
    message = str(getattr(error, 'orig', error)).lower()
    errors = {}
    if 'email' in message:
        errors['email'] = ['Email already exists.']
    if 'username' in message:
        errors.setdefault('username', []).append('Username already exists.')
    if not errors:
        errors['_schema'] = ['Unique constraint violated.']
    return jsonify({'errors': errors}), 409
