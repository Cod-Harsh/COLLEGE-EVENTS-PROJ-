from flask import Flask, render_template, redirect, url_for, flash, request, abort
from config import Config
from models import db, User, Event, Registration
from forms import LoginForm, RegisterForm, EventForm
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    login = LoginManager()
    login.login_view = 'login'
    login.init_app(app)

    @login.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ✅ Initialize DB and create default admin (Flask 3.x safe)
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='admin@college.edu').first():
            admin = User(
                name='Admin',
                email='admin@college.edu',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()

    # ---------------- ROUTES ---------------- #

    @app.route('/')
    def index():
        now = datetime.utcnow()
        events = Event.query.order_by(Event.date.asc()).all()
        return render_template('index.html', events=events)

    @app.route('/event/<int:event_id>')
    def view_event(event_id):
        event = Event.query.get_or_404(event_id)
        registered = None
        if current_user.is_authenticated:
            registered = Registration.query.filter_by(user_id=current_user.id, event_id=event.id).first()
        return render_template('view_event.html', event=event, registered=registered)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        form = RegisterForm()
        if form.validate_on_submit():
            if User.query.filter_by(email=form.email.data).first():
                flash('Email already registered. Please login.', 'warning')
                return redirect(url_for('login'))
            user = User(
                name=form.name.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data)
            )
            db.session.add(user)
            db.session.commit()
            flash('Registration successful. Please login.', 'success')
            return redirect(url_for('login'))
        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                flash('Logged in successfully.', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            flash('Invalid email or password.', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    @app.route('/admin')
    @login_required
    def admin_dashboard():
        if not current_user.is_admin:
            abort(403)
        events = Event.query.order_by(Event.date.asc()).all()
        pending_regs = Registration.query.filter_by(status='pending').order_by(Registration.created_at.desc()).all()
        return render_template('admin_dashboard.html', events=events, pending_regs=pending_regs)

    @app.route('/admin/event/create', methods=['GET', 'POST'])
    @login_required
    def create_event():
        if not current_user.is_admin:
            abort(403)
        form = EventForm()
        if form.validate_on_submit():
            event = Event(
                title=form.title.data,
                description=form.description.data,
                venue=form.venue.data,
                date=form.date.data,
                capacity=form.capacity.data if form.capacity.data else None
            )
            db.session.add(event)
            db.session.commit()
            flash('Event created successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        return render_template('create_event.html', form=form)

    @app.route('/admin/event/<int:event_id>/delete', methods=['POST'])
    @login_required
    def delete_event(event_id):
        if not current_user.is_admin:
            abort(403)
        event = Event.query.get_or_404(event_id)
        db.session.delete(event)
        db.session.commit()
        flash('Event deleted.', 'info')
        return redirect(url_for('admin_dashboard'))

    @app.route('/event/<int:event_id>/register', methods=['POST'])
    @login_required
    def register_for_event(event_id):
        event = Event.query.get_or_404(event_id)
        if event.capacity:
            accepted_count = Registration.query.filter_by(event_id=event.id, status='accepted').count()
            if accepted_count >= event.capacity:
                flash('This event is full.', 'warning')
                return redirect(url_for('view_event', event_id=event.id))
        existing = Registration.query.filter_by(user_id=current_user.id, event_id=event.id).first()
        if existing:
            flash('You already registered for this event.', 'info')
            return redirect(url_for('view_event', event_id=event.id))
        reg = Registration(user_id=current_user.id, event_id=event.id, status='pending')
        db.session.add(reg)
        db.session.commit()
        flash('Registration submitted. Admin will confirm.', 'success')
        return redirect(url_for('my_registrations'))

    @app.route('/my-registrations')
    @login_required
    def my_registrations():
        regs = Registration.query.filter_by(user_id=current_user.id).order_by(Registration.created_at.desc()).all()
        return render_template('my_registrations.html', regs=regs)

    @app.route('/admin/registration/<int:reg_id>/action', methods=['POST'])
    @login_required
    def registration_action(reg_id):
        if not current_user.is_admin:
            abort(403)
        action = request.form.get('action')
        reg = Registration.query.get_or_404(reg_id)
        if action == 'accept':
            reg.status = 'accepted'
        elif action == 'reject':
            reg.status = 'rejected'
        elif action == 'cancel':
            reg.status = 'cancelled'
        db.session.commit()
        flash('Registration updated.', 'info')
        return redirect(url_for('admin_dashboard'))

    @app.route('/past-events')
    def past_events():
        now = datetime.utcnow()
        events = Event.query.filter(Event.date < now).order_by(Event.date.desc()).all()
        return render_template('past_events.html', events=events)

    @app.route('/upcoming-events')
    def upcoming_events():
        now = datetime.utcnow()
        events = Event.query.filter(Event.date >= now).order_by(Event.date.asc()).all()
        return render_template('upcoming_events.html', events=events)

    @app.route('/contacts')
    def contacts():
        return render_template('contacts.html')

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
