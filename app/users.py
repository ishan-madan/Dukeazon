from flask import render_template, redirect, url_for, flash, request
from urllib.parse import urlparse as url_parse
from flask_login import login_user, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, RadioField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length, Regexp

from .models.user import User
from .models.subscription import Subscription


from flask import Blueprint
bp = Blueprint('users', __name__)

def format_full_address(street, city, state, zip_code):
    def clean(value):
        return (value or '').strip()
    street = clean(street)
    city = clean(city)
    state = clean(state).upper()
    zip_code = clean(zip_code)
    parts = []
    if street:
        parts.append(street)
    if city:
        parts.append(city)
    state_zip = ' '.join([part for part in (state, zip_code) if part])
    if state_zip:
        parts.append(state_zip)
    return ', '.join(parts)


def parse_address(address):
    result = {'street': '', 'city': '', 'state': '', 'zip_code': ''}
    if not address:
        return result
    segments = [seg.strip() for seg in address.split(',') if seg.strip()]
    if not segments:
        return result
    state_zip_segment = ''
    if len(segments) >= 3:
        result['street'] = ', '.join(segments[:-2])
        result['city'] = segments[-2]
        state_zip_segment = segments[-1]
    elif len(segments) == 2:
        result['street'] = segments[0]
        possible = segments[1]
        tokens = possible.split()
        if len(tokens) >= 2 and len(tokens[0]) == 2:
            state_zip_segment = possible
        else:
            result['city'] = possible
    else:
        result['street'] = segments[0]
    tokens = state_zip_segment.split()
    if tokens:
        result['state'] = tokens[0].upper()
        if len(tokens) > 1:
            result['zip_code'] = ' '.join(tokens[1:])
    return result

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
    street = StringField('Street Address', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired(), Length(min=2, max=2, message='Use 2-letter state code.')])
    zip_code = StringField('ZIP Code', validators=[
        DataRequired(),
        Regexp(r'^\d{5}(?:-\d{4})?$', message='Enter a valid ZIP code (##### or #####-####).')
    ])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Confirm Password', validators=[DataRequired(),
                                       EqualTo('password')])
    user_type = RadioField('Account Type', choices=[('buyer', 'Buyer'), ('seller', 'Seller')], validators=[DataRequired()])
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
        is_seller = form.user_type.data == 'seller'
        address = format_full_address(form.street.data,
                                      form.city.data,
                                      form.state.data,
                                      form.zip_code.data)
        if User.register(form.email.data,
                         form.password.data,
                         form.firstname.data,
                         form.lastname.data,
                         address,
                         is_seller=is_seller):
            flash('Registration Successful. Please login to access your account', 'success')
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
    street = StringField('Street Address', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired(), Length(min=2, max=2, message='Use 2-letter state code.')])
    zip_code = StringField('ZIP Code', validators=[
        DataRequired(),
        Regexp(r'^\d{5}(?:-\d{4})?$', message='Enter a valid ZIP code (##### or #####-####).')
    ])
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
    subscriptions = Subscription.get_active_by_user(current_user.id)
    address_parts = parse_address(current_user.address)

                                             
    if request.method == 'GET':
        update_form.firstname.data = current_user.firstname
        update_form.lastname.data = current_user.lastname
        update_form.email.data = current_user.email
        update_form.street.data = address_parts['street']
        update_form.city.data = address_parts['city']
        update_form.state.data = address_parts['state']
        update_form.zip_code.data = address_parts['zip_code']

                                         
    if update_form.submit.data and update_form.validate_on_submit():
        formatted_address = format_full_address(
            update_form.street.data,
            update_form.city.data,
            update_form.state.data,
            update_form.zip_code.data
        )
        User.update_account(
            uid=current_user.id,
            firstname=update_form.firstname.data,
            lastname=update_form.lastname.data,
            email=update_form.email.data,
            address=formatted_address
        )
        current_user.address = formatted_address
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
                           user=current_user,
                           subscriptions=subscriptions,
                           address_display=format_full_address(
                               address_parts['street'],
                               address_parts['city'],
                               address_parts['state'],
                               address_parts['zip_code']
                           ))


@bp.route('/subscriptions/<int:subscription_id>/cancel', methods=['POST'])
@login_required
def cancel_subscription(subscription_id):
    if Subscription.cancel(subscription_id, current_user.id):
        flash('Subscription canceled.', 'success')
    else:
        flash('Unable to cancel that subscription.', 'danger')
    return redirect(url_for('users.account'))
