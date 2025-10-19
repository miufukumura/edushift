from __future__ import annotations

from datetime import datetime

from flask import (
    Blueprint,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from . import db
from .models import Lesson, Shift, Student, User

bp = Blueprint("main", __name__)


@bp.before_app_request
def load_logged_in_user() -> None:
    """Attach the logged-in user to flask.g for later use."""
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id else None


@bp.route("/", methods=["GET"], endpoint="index")
def index():
    """Redirect users to the appropriate top page based on their role."""
    role = session.get("user_role")
    if role == "admin":
        return redirect(url_for("main.admin_dashboard"))
    if role == "teacher":
        return redirect(url_for("main.teacher_shift"))
    return redirect(url_for("main.login"))


@bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    """Handle user login."""
    if session.get("user_role"):
        return redirect(url_for("main.index"))

    error: str | None = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        try:
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                session["user_id"] = user.id
                session["user_role"] = user.role
                session["user_name"] = user.name
                return redirect(url_for("main.index"))
            error = "メールアドレスまたはパスワードが違います。"
        except SQLAlchemyError as exc:
            db.session.rollback()
            print(f"Login error: {exc}")
            error = "サーバー側で予期せぬエラーが発生しました。"

    return render_template("login.html", error=error)


@bp.route("/register", methods=["GET", "POST"], endpoint="register")
def register():
    """Allow teachers to create a basic account."""
    if session.get("user_id"):
        return redirect(url_for("main.index"))

    error: str | None = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if len(password) < 6:
            error = "パスワードは6文字以上で設定してください。"
            return render_template("register.html", error=error)

        try:
            if User.query.filter_by(email=email).first():
                error = "このメールアドレスは既に使用されています。"
            else:
                user = User(name=name, email=email, role="teacher")
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                return redirect(url_for("main.login"))
        except IntegrityError:
            db.session.rollback()
            error = "このメールアドレスは既に使用されています。"
        except SQLAlchemyError as exc:
            db.session.rollback()
            print(f"Register error: {exc}")
            error = "サーバー側で予期せぬエラーが発生しました。"

    return render_template("register.html", error=error)


@bp.route("/logout", methods=["GET"], endpoint="logout")
def logout():
    """Log out and return to the login page."""
    session.clear()
    return redirect(url_for("main.login"))


@bp.route("/teacher/shift", methods=["GET", "POST"], endpoint="teacher_shift")
def teacher_shift():
    """Allow teachers to register, edit, and review their shifts."""
    if session.get("user_role") not in {"teacher", "admin"}:
        return redirect(url_for("main.login"))

    user_id = session["user_id"]
    error: str | None = None
    form_data: dict[str, str] = {
        "shift_id": "",
        "date": "",
        "start_time": "17:00",
        "end_time": "21:00",
    }
    is_edit_mode = False

    edit_id = request.args.get("edit", type=int)
    if edit_id is not None:
        edit_query = Shift.query.filter_by(id=edit_id)
        if session.get("user_role") == "teacher":
            edit_query = edit_query.filter_by(user_id=user_id)
        edit_shift = edit_query.first()
        if edit_shift:
            is_edit_mode = True
            form_data.update(
                {
                    "shift_id": str(edit_shift.id),
                    "date": edit_shift.date.strftime("%Y-%m-%d"),
                    "start_time": edit_shift.start_time,
                    "end_time": edit_shift.end_time,
                }
            )
        else:
            error = "編集対象のシフトが見つかりません。"

    if request.method == "POST":
        shift_id = request.form.get("shift_id")
        date_str = request.form.get("date", "")
        start_time = request.form.get("start_time", "")
        end_time = request.form.get("end_time", "")

        form_data.update(
            {
                "shift_id": shift_id or "",
                "date": date_str,
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        if shift_id:
            is_edit_mode = True

        try:
            shift_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            error = "日付の形式が正しくありません。"
        else:
            try:
                if shift_id:
                    shift = Shift.query.filter_by(id=int(shift_id)).first()
                    if not shift or (
                        session.get("user_role") == "teacher" and shift.user_id != user_id
                    ):
                        error = "編集対象のシフトが見つかりません。"
                    else:
                        shift.date = shift_date
                        shift.start_time = start_time
                        shift.end_time = end_time
                        db.session.commit()
                        return redirect(url_for("main.teacher_shift"))
                else:
                    shift = Shift(
                        user_id=user_id,
                        date=shift_date,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    db.session.add(shift)
                    db.session.commit()
                    return redirect(url_for("main.teacher_shift"))
            except SQLAlchemyError as exc:
                db.session.rollback()
                print(f"Shift save error: {exc}")
                error = "シフトの保存中にエラーが発生しました。"

    shifts = (
        Shift.query.filter_by(user_id=user_id)
        .order_by(Shift.date.asc(), Shift.start_time.asc())
        .all()
    )

    return render_template(
        "teacher_shift.html",
        shifts=shifts,
        error=error,
        form_data=form_data,
        is_edit_mode=is_edit_mode,
    )


@bp.route("/teacher/shift/delete/<int:shift_id>", methods=["POST"], endpoint="delete_shift")
def delete_shift(shift_id: int):
    """Delete a shift."""
    if session.get("user_role") not in {"teacher", "admin"}:
        return redirect(url_for("main.login"))

    query = Shift.query.filter_by(id=shift_id)
    if session.get("user_role") == "teacher":
        query = query.filter_by(user_id=session["user_id"])

    shift = query.first()
    if shift:
        try:
            db.session.delete(shift)
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            print(f"Shift deletion error: {exc}")

    return redirect(url_for("main.teacher_shift"))


@bp.route("/lesson/manage", methods=["GET", "POST"], endpoint="lesson_manage")
def lesson_manage():
    """Register lessons and show recent history."""
    if not session.get("user_id"):
        return redirect(url_for("main.login"))

    error: str | None = None

    if request.method == "POST":
        student_id = request.form.get("student_id")
        teacher_id = request.form.get("teacher_id")
        date_str = request.form.get("date", "")
        status = request.form.get("status", "")
        notes = request.form.get("notes", "").strip()

        try:
            lesson_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            lesson = Lesson(
                student_id=int(student_id),
                teacher_id=int(teacher_id),
                date=lesson_date,
                status=status,
                notes=notes or None,
            )
            db.session.add(lesson)
            db.session.commit()
            return redirect(url_for("main.lesson_manage"))
        except (TypeError, ValueError):
            error = "登録内容を確認してください。"
        except SQLAlchemyError as exc:
            db.session.rollback()
            print(f"Lesson registration error: {exc}")
            error = "授業登録中にエラーが発生しました。"

    students = Student.query.order_by(Student.name.asc()).all()
    teachers = User.query.filter_by(role="teacher").order_by(User.name.asc()).all()

    lessons_query = (
        db.session.query(
            Lesson.id,
            Lesson.date,
            Lesson.status,
            Lesson.notes,
            Student.name.label("student_name"),
            User.name.label("teacher_name"),
        )
        .join(Student, Lesson.student_id == Student.id)
        .join(User, Lesson.teacher_id == User.id)
        .order_by(Lesson.date.desc())
        .limit(50)
    )
    lessons = [
        {
            "id": row.id,
            "date": row.date,
            "status": row.status,
            "notes": row.notes,
            "student_name": row.student_name,
            "teacher_name": row.teacher_name,
        }
        for row in lessons_query
    ]

    return render_template(
        "lesson_manage.html",
        students=students,
        teachers=teachers,
        lessons=lessons,
        error=error,
    )


@bp.route("/admin/dashboard", methods=["GET"], endpoint="admin_dashboard")
def admin_dashboard():
    """Show recent shifts and lesson changes for administrators."""
    if session.get("user_role") != "admin":
        return redirect(url_for("main.login"))

    all_shifts_query = (
        db.session.query(
            Shift.date,
            Shift.start_time,
            Shift.end_time,
            User.name.label("teacher_name"),
        )
        .join(User, Shift.user_id == User.id)
        .order_by(Shift.date.asc(), Shift.start_time.asc())
        .limit(50)
    )
    all_shifts = [
        {
            "date": row.date,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "teacher_name": row.teacher_name,
        }
        for row in all_shifts_query
    ]

    recent_changes_query = (
        db.session.query(
            Lesson.date,
            Lesson.status,
            Student.name.label("student_name"),
            User.name.label("teacher_name"),
        )
        .join(Student, Lesson.student_id == Student.id)
        .join(User, Lesson.teacher_id == User.id)
        .filter(Lesson.status.in_(["欠席", "振替"]))
        .order_by(Lesson.date.desc())
        .limit(30)
    )
    recent_changes = [
        {
            "date": row.date,
            "status": row.status,
            "student_name": row.student_name,
            "teacher_name": row.teacher_name,
        }
        for row in recent_changes_query
    ]

    return render_template(
        "admin_dashboard.html",
        all_shifts=all_shifts,
        recent_changes=recent_changes,
    )


@bp.route("/manage/users", methods=["GET", "POST"], endpoint="manage_users")
def manage_users():
    """Manage teacher and student accounts."""
    if session.get("user_role") != "admin":
        return redirect(url_for("main.index"))

    error: str | None = None

    if request.method == "POST":
        action = request.form.get("action")

        try:
            if action == "add_user":
                name = request.form.get("name", "").strip()
                email = request.form.get("email", "").strip()
                password = request.form.get("password", "")
                role = request.form.get("role", "teacher")

                user = User(name=name, email=email, role=role)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()

            elif action == "add_student":
                name = request.form.get("name", "").strip()
                grade = request.form.get("grade", "").strip()
                student = Student(name=name, grade=grade or None)
                db.session.add(student)
                db.session.commit()

            elif action == "delete_user":
                user_id = int(request.form.get("id"))
                db.session.query(Shift).filter_by(user_id=user_id).delete()
                db.session.query(User).filter_by(id=user_id).delete()
                db.session.commit()

            elif action == "delete_student":
                student_id = int(request.form.get("id"))
                db.session.query(Lesson).filter_by(student_id=student_id).delete()
                db.session.query(Student).filter_by(id=student_id).delete()
                db.session.commit()
        except IntegrityError:
            db.session.rollback()
            error = "データの重複エラーが発生しました。"
        except (TypeError, ValueError):
            db.session.rollback()
            error = "入力内容を確認してください。"
        except SQLAlchemyError as exc:
            db.session.rollback()
            print(f"User management error: {exc}")
            error = f"処理中にエラーが発生しました: {exc}"

        return redirect(url_for("main.manage_users", error=error))

    error = request.args.get("error")
    users = User.query.order_by(User.role.desc(), User.name.asc()).all()
    students = Student.query.order_by(Student.name.asc()).all()

    return render_template(
        "manage_users.html",
        users=users,
        students=students,
        error=error,
    )
