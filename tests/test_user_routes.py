import unittest

from flask import Flask

from src.models.user import db
from src.routes.user import user_bp


class UserRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)

        with self.app.app_context():
            db.create_all()

        self.app.register_blueprint(user_bp, url_prefix='/api')
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_create_user_requires_valid_payload(self):
        response = self.client.post('/api/users', json={'email': 'not-an-email'})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('username', data['errors'])
        self.assertIn('email', data['errors'])

    def test_create_user_rejects_duplicate_email(self):
        create_response = self.client.post(
            '/api/users',
            json={'username': 'alice', 'email': 'alice@example.com'},
        )
        self.assertEqual(create_response.status_code, 201)

        duplicate_response = self.client.post(
            '/api/users',
            json={'username': 'bob', 'email': 'alice@example.com'},
        )
        self.assertEqual(duplicate_response.status_code, 409)
        duplicate_data = duplicate_response.get_json()
        self.assertIn('email', duplicate_data['errors'])

    def test_partial_update_allows_updating_subset_of_fields(self):
        create_response = self.client.post(
            '/api/users',
            json={'username': 'charlie', 'email': 'charlie@example.com'},
        )
        user_id = create_response.get_json()['id']

        update_response = self.client.put(
            f'/api/users/{user_id}',
            json={'email': 'charlie.new@example.com'},
        )

        self.assertEqual(update_response.status_code, 200)
        updated_user = update_response.get_json()
        self.assertEqual(updated_user['username'], 'charlie')
        self.assertEqual(updated_user['email'], 'charlie.new@example.com')


if __name__ == '__main__':
    unittest.main()
