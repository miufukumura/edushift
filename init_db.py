from app import create_app, db
from app.models import User


def init_db() -> None:
    """Create tables and ensure an admin user exists."""
    app = create_app()
    with app.app_context():
        db.create_all()

        admin_email = "admin@example.com"
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(name="管理者", email=admin_email, role="admin")
            admin.set_password("adminpass")
            db.session.add(admin)
            db.session.commit()


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
