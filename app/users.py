from flask import render_template, redirect, url_for, flash, request
from urllib.parse import urlparse as url_parse
from flask_login import login_user, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo

from .models.user import User


from flask import Blueprint
bp = Blueprint('users', __name__)


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by_auth(form.email.data, form.password.data)
        if user is None:
            flash('Invalid email or password')
            return redirect(url_for('users.login'))
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index.index')

        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


class RegistrationForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    address = StringField('Address', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Confirm Password', validators=[DataRequired(),
                                       EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        if User.email_exists(email.data):
            raise ValidationError('Already a user with this email.')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.register(form.email.data,
                         form.password.data,
                         form.firstname.data,
                         form.lastname.data,
                         form.address.data):
            flash('Congratulations, you are now a registered user!')
            return redirect(url_for('users.login'))
    return render_template('register.html', title='Register', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index.index'))


from flask_login import login_required
from .models.purchase import Purchase
from .models.order import Order

@bp.route('/purchases')
@login_required
def purchases():
    q = request.args.get("q")  # GET parameter ?q=abc
    purchases = Order.get_user_purchases(current_user.id, q=q)
    
    return render_template(
        'purchases.html',
        title="My Purchases",
        purchases=purchases,
        q=q
    )

class UpdateAccountForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    address = StringField('Address', validators=[DataRequired()])
    submit = SubmitField('Update')

    def validate_email(self, email):
                                  
        if email.data != current_user.email and User.email_exists(email.data):
            raise ValidationError('A user with this email already exists.')

class BalanceForm(FlaskForm):
    amount = StringField('Amount', validators=[DataRequired()])
    submit_add = SubmitField('Add Funds')
    submit_withdraw = SubmitField('Withdraw Funds')

@bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    update_form = UpdateAccountForm()
    balance_form = BalanceForm()

                                             
    if request.method == 'GET':
        update_form.firstname.data = current_user.firstname
        update_form.lastname.data = current_user.lastname
        update_form.email.data = current_user.email
        update_form.address.data = current_user.address

                                         
    if update_form.submit.data and update_form.validate_on_submit():
        User.update_account(
            uid=current_user.id,
            firstname=update_form.firstname.data,
            lastname=update_form.lastname.data,
            email=update_form.email.data,
            address=update_form.address.data
        )
        flash('Your account information has been updated.')
        return redirect(url_for('users.account'))

                            
    if balance_form.validate_on_submit():
        try:
            amount = float(balance_form.amount.data)
        except ValueError:
            flash('Please enter a numeric amount.', 'danger')
            return redirect(url_for('users.account'))
        if amount <= 0:
            flash('Amount must be positive.', 'danger')
            return redirect(url_for('users.account'))

                   
        if balance_form.submit_add.data:
            User.add_balance(current_user.id, amount)
            flash(f'Added ${amount:.2f} to your balance.')

                        
        if balance_form.submit_withdraw.data:
            if amount > current_user.balance:
                flash('Not enough balance to withdraw.')
            else:
                User.withdraw_balance(current_user.id, amount)
                flash(f'Withdrew ${amount:.2f}.')

        return redirect(url_for('users.account'))

    return render_template('account.html',
                           update_form=update_form,
                           balance_form=balance_form,
                           user=current_user)
