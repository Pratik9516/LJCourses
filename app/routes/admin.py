from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.db import SessionLocal
from app.services import (
    get_all_courses, get_all_categories, create_category,
    create_course, create_lesson, get_course_by_id,
    get_lessons_by_course, get_all_lessons
)
from app.models import User, UserRole
import re

bp = Blueprint('admin', __name__, url_prefix='/admin')

ADMIN_SECRET = 'pratik@admin123'  # Change this to your own secret!

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated

# ─── LOGIN ───
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_SECRET:
            session['is_admin'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Wrong password!', 'danger')
    return render_template('admin/login.html')

@bp.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin.login'))

# ─── DASHBOARD ───
@bp.route('/')
@admin_required
def dashboard():
    db = SessionLocal()
    try:
        courses = get_all_courses(db)
        categories = get_all_categories(db)
        users = db.query(User).all()
        return render_template('admin/dashboard.html',
                             courses=courses,
                             categories=categories,
                             users=users)
    finally:
        db.close()

# ─── ADD CATEGORY ───
@bp.route('/category/add', methods=['GET', 'POST'])
@admin_required
def add_category():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Category name required!', 'danger')
        else:
            db = SessionLocal()
            try:
                slug = slugify(name)
                create_category(db, name=name, slug=slug)
                flash(f'Category "{name}" created!', 'success')
                return redirect(url_for('admin.dashboard'))
            except ValueError as e:
                flash(str(e), 'danger')
            finally:
                db.close()
    return render_template('admin/add_category.html')

# ─── ADD COURSE ───
@bp.route('/course/add', methods=['GET', 'POST'])
@admin_required
def add_course():
    db = SessionLocal()
    try:
        categories = get_all_categories(db)
        instructors = db.query(User).filter(
            User.role.in_([UserRole.INSTRUCTOR, UserRole.HOD])
        ).all()

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            category_id = request.form.get('category_id')
            instructor_id = request.form.get('instructor_id')
            description = request.form.get('description', '').strip()
            small_description = request.form.get('small_description', '').strip()
            difficulty_level = request.form.get('difficulty_level', 'Beginner')
            duration_hours = request.form.get('duration_hours', 0)
            thumbnail = request.form.get('thumbnail', '').strip()

            if not title or not category_id or not instructor_id:
                flash('Title, Category and Instructor are required!', 'danger')
            else:
                slug = slugify(title)
                try:
                    course = create_course(
                        db,
                        instructor_id=instructor_id,
                        category_id=category_id,
                        title=title,
                        slug=slug,
                        description=description,
                        small_description=small_description,
                        difficulty_level=difficulty_level,
                        duration_hours=float(duration_hours) if duration_hours else None,
                        thumbnail=thumbnail or None,
                        rating=0.0
                    )
                    flash(f'Course "{title}" created!', 'success')
                    return redirect(url_for('admin.add_lesson', course_id=str(course.id)))
                except ValueError as e:
                    flash(str(e), 'danger')

        return render_template('admin/add_course.html',
                             categories=categories,
                             instructors=instructors)
    finally:
        db.close()

# ─── ADD LESSON ───
@bp.route('/lesson/add/<course_id>', methods=['GET', 'POST'])
@admin_required
def add_lesson(course_id):
    db = SessionLocal()
    try:
        course = get_course_by_id(db, course_id)
        if not course:
            flash('Course not found!', 'danger')
            return redirect(url_for('admin.dashboard'))

        existing_lessons = get_lessons_by_course(db, course_id)

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            video_url = request.form.get('video_url', '').strip()
            description = request.form.get('description', '').strip()
            video_duration = request.form.get('video_duration', 0)
            order = len(existing_lessons) + 1

            if not title:
                flash('Lesson title required!', 'danger')
            else:
                create_lesson(
                    db,
                    course_id=course_id,
                    title=title,
                    order=order,
                    video_url=video_url or None,
                    description=description or None,
                    video_duration=int(video_duration) if video_duration else None
                )
                flash(f'Lesson "{title}" added!', 'success')
                existing_lessons = get_lessons_by_course(db, course_id)

            if 'add_more' not in request.form:
                return redirect(url_for('admin.dashboard'))

        return render_template('admin/add_lesson.html',
                             course=course,
                             lessons=existing_lessons)
    finally:
        db.close()

# ─── ADD INSTRUCTOR ───
@bp.route('/instructor/add', methods=['GET', 'POST'])
@admin_required
def add_instructor():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        designation = request.form.get('designation', '').strip()

        if not full_name or not email or not password:
            flash('Name, Email and Password required!', 'danger')
        else:
            db = SessionLocal()
            try:
                existing = db.query(User).filter(User.email == email).first()
                if existing:
                    flash('Email already exists!', 'danger')
                else:
                    user = User(
                        full_name=full_name,
                        email=email,
                        role=UserRole.INSTRUCTOR,
                        designation=designation or None,
                        is_active=True
                    )
                    user.set_password(password)
                    db.add(user)
                    db.commit()
                    flash(f'Instructor "{full_name}" created!', 'success')
                    return redirect(url_for('admin.dashboard'))
            except Exception as e:
                db.rollback()
                flash(str(e), 'danger')
            finally:
                db.close()

    return render_template('admin/add_instructor.html')