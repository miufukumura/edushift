from datetime import date

from werkzeug.security import check_password_hash, generate_password_hash

from . import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    shifts = db.relationship(
        "Shift",
        back_populates="teacher",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    lessons = db.relationship(
        "Lesson",
        back_populates="teacher",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="Lesson.teacher_id",
    )

    def set_password(self, raw_password: str) -> None:
        self.password = generate_password_hash(raw_password, method="pbkdf2:sha256")

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password, raw_password)


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    grade = db.Column(db.String(50))

    lessons = db.relationship(
        "Lesson",
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class Shift(db.Model):
    __tablename__ = "shifts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)

    teacher = db.relationship("User", back_populates="shifts")


class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)

    student = db.relationship("Student", back_populates="lessons")
    teacher = db.relationship("User", back_populates="lessons", foreign_keys=[teacher_id])
